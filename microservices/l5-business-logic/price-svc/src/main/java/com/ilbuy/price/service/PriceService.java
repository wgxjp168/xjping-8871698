package com.ilbuy.price.service;

import com.ilbuy.price.dto.*;
import com.ilbuy.price.model.entity.BulkPriceTier;
import com.ilbuy.price.model.entity.PriceAlert;
import com.ilbuy.price.model.entity.PriceRecord;
import com.ilbuy.price.model.entity.PriceTrend;
import com.ilbuy.price.repository.BulkPriceTierRepository;
import com.ilbuy.price.repository.PriceAlertRepository;
import com.ilbuy.price.repository.PriceRecordRepository;
import com.ilbuy.price.repository.PriceTrendRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class PriceService {

    private static final String CACHE_HISTORY_PREFIX    = "price:history:";
    private static final String CACHE_TREND_PREFIX      = "price:trend:";
    private static final String CACHE_COMPARE_PREFIX    = "price:compare:";
    private static final String CACHE_BULK_TIERS_PREFIX = "price:bulk-tiers:";

    private final PriceRecordRepository    priceRecordRepository;
    private final PriceAlertRepository     priceAlertRepository;
    private final PriceTrendRepository     priceTrendRepository;
    private final BulkPriceTierRepository  bulkPriceTierRepository;
    private final RedisTemplate<String, Object> redisTemplate;

    @Value("${price.cache.history-ttl-minutes:5}")
    private long historyTtlMinutes;

    @Value("${price.cache.trend-ttl-hours:1}")
    private long trendTtlHours;

    @Value("${price.cache.compare-ttl-minutes:5}")
    private long compareTtlMinutes;

    // -------------------------------------------------------------------------
    // Price History
    // -------------------------------------------------------------------------

    @Transactional(readOnly = true)
    public PriceHistoryDTO getPriceHistory(Long canonicalId, String platform, int days) {
        String cacheKey = CACHE_HISTORY_PREFIX + canonicalId + ":" + platform + ":" + days;

        Object cached = redisTemplate.opsForValue().get(cacheKey);
        if (cached instanceof PriceHistoryDTO dto) {
            log.debug("Cache hit for price history: {}", cacheKey);
            return dto;
        }

        log.debug("Cache miss for price history: {}", cacheKey);

        LocalDateTime since = LocalDateTime.now().minusDays(days);
        List<PriceRecord> records;

        if (platform != null && !platform.isBlank()) {
            records = priceRecordRepository
                .findByCanonicalIdAndPlatformAndRecordedAtAfterOrderByRecordedAtDesc(
                    canonicalId, platform, since);
        } else {
            records = priceRecordRepository
                .findByCanonicalIdAndRecordedAtAfterOrderByRecordedAtDesc(canonicalId, since);
        }

        List<PricePointDTO> points = records.stream()
            .map(r -> PricePointDTO.builder()
                .price(r.getPrice())
                .originalPrice(r.getOriginalPrice())
                .recordedAt(r.getRecordedAt())
                .build())
            .collect(Collectors.toList());

        PriceHistoryDTO result = PriceHistoryDTO.builder()
            .canonicalId(canonicalId)
            .platform(platform)
            .points(points)
            .build();

        redisTemplate.opsForValue().set(cacheKey, result, historyTtlMinutes, TimeUnit.MINUTES);

        return result;
    }

    // -------------------------------------------------------------------------
    // Price Trend
    // -------------------------------------------------------------------------

    @Transactional(readOnly = true)
    public PriceTrendDTO getPriceTrend(Long canonicalId, String platform, String granularity, int days) {
        String cacheKey = CACHE_TREND_PREFIX + canonicalId + ":" + platform + ":" + granularity + ":" + days;

        Object cached = redisTemplate.opsForValue().get(cacheKey);
        if (cached instanceof PriceTrendDTO dto) {
            log.debug("Cache hit for price trend: {}", cacheKey);
            return dto;
        }

        log.debug("Cache miss for price trend: {}", cacheKey);

        Date since = Date.from(
            LocalDateTime.now().minusDays(days).atZone(ZoneId.systemDefault()).toInstant());

        List<PriceTrend> trends;
        String effectivePlatform = (platform != null && !platform.isBlank()) ? platform : "";

        if ("WEEKLY".equalsIgnoreCase(granularity)) {
            if (!effectivePlatform.isBlank()) {
                trends = priceTrendRepository.findWeeklyTrend(canonicalId, effectivePlatform, since);
            } else {
                // Fall back to DAILY if no platform specified
                trends = priceTrendRepository.findByCanonicalIdAndDateAfterOrderByDateAsc(canonicalId, since);
            }
        } else if ("MONTHLY".equalsIgnoreCase(granularity)) {
            if (!effectivePlatform.isBlank()) {
                trends = priceTrendRepository.findMonthlyTrend(canonicalId, effectivePlatform, since);
            } else {
                trends = priceTrendRepository.findByCanonicalIdAndDateAfterOrderByDateAsc(canonicalId, since);
            }
        } else {
            // DAILY (default)
            if (!effectivePlatform.isBlank()) {
                trends = priceTrendRepository.findByCanonicalIdAndPlatformAndDateAfterOrderByDateAsc(
                    canonicalId, effectivePlatform, since);
            } else {
                trends = priceTrendRepository.findByCanonicalIdAndDateAfterOrderByDateAsc(canonicalId, since);
            }
        }

        List<TrendPointDTO> points = trends.stream()
            .map(t -> TrendPointDTO.builder()
                .date(t.getDate())
                .minPrice(t.getMinPrice())
                .maxPrice(t.getMaxPrice())
                .avgPrice(t.getAvgPrice())
                .build())
            .collect(Collectors.toList());

        PriceTrendDTO result = PriceTrendDTO.builder()
            .canonicalId(canonicalId)
            .platform(platform)
            .granularity(granularity != null ? granularity.toUpperCase() : "DAILY")
            .points(points)
            .build();

        redisTemplate.opsForValue().set(cacheKey, result, trendTtlHours, TimeUnit.HOURS);

        return result;
    }

    // -------------------------------------------------------------------------
    // Cross-Platform Price Comparison
    // -------------------------------------------------------------------------

    @Transactional(readOnly = true)
    public CrossPlatformPriceDTO getCrossPlatformComparison(Long canonicalId) {
        String cacheKey = CACHE_COMPARE_PREFIX + canonicalId;

        Object cached = redisTemplate.opsForValue().get(cacheKey);
        if (cached instanceof CrossPlatformPriceDTO dto) {
            log.debug("Cache hit for price comparison: {}", cacheKey);
            return dto;
        }

        log.debug("Cache miss for price comparison: {}", cacheKey);

        List<PriceRecord> latestPerPlatform = priceRecordRepository
            .findLatestPricePerPlatform(canonicalId);

        if (latestPerPlatform.isEmpty()) {
            CrossPlatformPriceDTO empty = CrossPlatformPriceDTO.builder()
                .canonicalId(canonicalId)
                .platforms(Collections.emptyList())
                .build();
            redisTemplate.opsForValue().set(cacheKey, empty, compareTtlMinutes, TimeUnit.MINUTES);
            return empty;
        }

        // Build platform price DTOs
        List<PlatformPriceDTO> platformPrices = latestPerPlatform.stream()
            .map(r -> {
                BigDecimal discount = null;
                if (r.getOriginalPrice() != null
                    && r.getOriginalPrice().compareTo(BigDecimal.ZERO) > 0) {
                    discount = r.getPrice()
                        .divide(r.getOriginalPrice(), 4, RoundingMode.HALF_UP)
                        .multiply(BigDecimal.valueOf(100))
                        .setScale(2, RoundingMode.HALF_UP);
                }
                return PlatformPriceDTO.builder()
                    .platform(r.getPlatform())
                    .currentPrice(r.getPrice())
                    .originalPrice(r.getOriginalPrice())
                    .discount(discount)
                    .inStock(r.getInStock())
                    .lastUpdated(r.getRecordedAt())
                    .build();
            })
            // Sort by currentPrice ASC
            .sorted(Comparator.comparing(PlatformPriceDTO::getCurrentPrice))
            .collect(Collectors.toList());

        BigDecimal lowestPrice  = platformPrices.get(0).getCurrentPrice();
        String lowestPlatform   = platformPrices.get(0).getPlatform();
        BigDecimal highestPrice = platformPrices.get(platformPrices.size() - 1).getCurrentPrice();

        BigDecimal priceDiff    = highestPrice.subtract(lowestPrice);
        BigDecimal priceDiffPct = BigDecimal.ZERO;
        if (lowestPrice.compareTo(BigDecimal.ZERO) > 0) {
            priceDiffPct = priceDiff
                .divide(lowestPrice, 4, RoundingMode.HALF_UP)
                .multiply(BigDecimal.valueOf(100))
                .setScale(2, RoundingMode.HALF_UP);
        }

        CrossPlatformPriceDTO result = CrossPlatformPriceDTO.builder()
            .canonicalId(canonicalId)
            .platforms(platformPrices)
            .lowestPlatform(lowestPlatform)
            .lowestPrice(lowestPrice)
            .priceDiff(priceDiff)
            .priceDiffPct(priceDiffPct)
            .build();

        redisTemplate.opsForValue().set(cacheKey, result, compareTtlMinutes, TimeUnit.MINUTES);

        return result;
    }

    // -------------------------------------------------------------------------
    // Price Alerts
    // -------------------------------------------------------------------------

    @Transactional
    public PriceAlertDTO createPriceAlert(Long userId, CreateAlertRequest request) {
        // Validate: targetPrice should be less than current price (if available)
        Optional<PriceRecord> latestRecord = Optional.empty();
        if (request.getPlatform() != null && !request.getPlatform().isBlank()) {
            latestRecord = priceRecordRepository
                .findFirstByCanonicalIdAndPlatformOrderByRecordedAtDesc(
                    request.getCanonicalId(), request.getPlatform());
        }

        latestRecord.ifPresent(record -> {
            if (request.getTargetPrice().compareTo(record.getPrice()) >= 0) {
                throw new IllegalArgumentException(
                    String.format("Target price %.2f must be less than current price %.2f",
                        request.getTargetPrice(), record.getPrice()));
            }
        });

        PriceAlert alert = PriceAlert.builder()
            .userId(userId)
            .canonicalId(request.getCanonicalId())
            .platform(request.getPlatform())
            .targetPrice(request.getTargetPrice())
            .triggered(false)
            .build();

        alert = priceAlertRepository.save(alert);
        log.info("Created price alert id={} for userId={} canonicalId={} targetPrice={}",
            alert.getId(), userId, request.getCanonicalId(), request.getTargetPrice());

        return toDto(alert);
    }

    @Transactional(readOnly = true)
    public List<PriceAlertDTO> getUserAlerts(Long userId) {
        return priceAlertRepository.findByUserIdOrderByCreatedAtDesc(userId)
            .stream()
            .map(this::toDto)
            .collect(Collectors.toList());
    }

    @Transactional
    public void deleteAlert(Long alertId, Long userId) {
        PriceAlert alert = priceAlertRepository.findByIdAndUserId(alertId, userId)
            .orElseThrow(() -> new IllegalArgumentException(
                "Price alert not found or does not belong to current user, id=" + alertId));
        priceAlertRepository.delete(alert);
        log.info("Deleted price alert id={} for userId={}", alertId, userId);
    }

    // -------------------------------------------------------------------------
    // B2B Bulk Price Tiers
    // -------------------------------------------------------------------------

    /**
     * Get all bulk price tiers for a product (optionally filtered by platform).
     * B2B scene: bulk buyers query tiered pricing before placing large orders.
     */
    @Transactional(readOnly = true)
    public List<BulkPriceTierDTO> getBulkPriceTiers(String canonicalId, String platform) {
        String cacheKey = CACHE_BULK_TIERS_PREFIX + canonicalId + ":" + (platform != null ? platform : "all");

        Object cached = redisTemplate.opsForValue().get(cacheKey);
        if (cached instanceof List<?> list) {
            log.debug("Cache hit for bulk price tiers: {}", cacheKey);
            //noinspection unchecked
            return (List<BulkPriceTierDTO>) list;
        }

        log.debug("Cache miss for bulk price tiers: {}", cacheKey);

        List<BulkPriceTier> tiers;
        if (platform != null && !platform.isBlank()) {
            tiers = bulkPriceTierRepository
                .findByCanonicalIdAndPlatformOrderByMinQuantityAsc(canonicalId, platform);
        } else {
            tiers = bulkPriceTierRepository
                .findByCanonicalIdOrderByMinQuantityAsc(canonicalId);
        }

        List<BulkPriceTierDTO> result = tiers.stream()
            .map(this::toBulkTierDto)
            .collect(Collectors.toList());

        redisTemplate.opsForValue().set(cacheKey, result, historyTtlMinutes, TimeUnit.MINUTES);

        return result;
    }

    /**
     * Query the applicable bulk price for a specific quantity.
     * B2B scene: finds the matching tier and computes totalAmount = unitPrice * quantity.
     * If no tier matches, returns null in tierApplied and uses standard retail price as fallback.
     */
    @Transactional(readOnly = true)
    public BulkPriceQueryResult queryBulkPrice(BulkPriceQueryRequest req) {
        List<BulkPriceTier> tiers;
        if (req.getPlatform() != null && !req.getPlatform().isBlank()) {
            tiers = bulkPriceTierRepository
                .findByCanonicalIdAndPlatformOrderByMinQuantityAsc(req.getCanonicalId(), req.getPlatform());
        } else {
            tiers = bulkPriceTierRepository
                .findByCanonicalIdOrderByMinQuantityAsc(req.getCanonicalId());
        }

        LocalDate today = LocalDate.now();

        // Find the matching tier: minQuantity <= quantity <= maxQuantity (null means unlimited)
        // Also filter by validity dates
        BulkPriceTier matched = tiers.stream()
            .filter(t -> t.getMinQuantity() <= req.getQuantity()
                && (t.getMaxQuantity() == null || t.getMaxQuantity() >= req.getQuantity())
                && (t.getValidFrom() == null || !t.getValidFrom().isAfter(today))
                && (t.getValidUntil() == null || !t.getValidUntil().isBefore(today)))
            .reduce((first, second) -> second) // take the last (highest minQuantity) matching tier
            .orElse(null);

        List<BulkPriceTierDTO> allTiers = tiers.stream()
            .map(this::toBulkTierDto)
            .collect(Collectors.toList());

        BigDecimal unitPrice;
        String currency;
        String unit;
        BulkPriceTierDTO tierApplied = null;

        if (matched != null) {
            unitPrice   = matched.getUnitPrice();
            currency    = matched.getCurrency();
            unit        = matched.getUnit();
            tierApplied = toBulkTierDto(matched);
        } else {
            // Fall back to standard retail price from the most recent PriceRecord
            String effectivePlatform = (req.getPlatform() != null && !req.getPlatform().isBlank())
                ? req.getPlatform() : null;
            BigDecimal retailPrice = null;
            if (effectivePlatform != null) {
                retailPrice = priceRecordRepository
                    .findFirstByCanonicalIdAndPlatformOrderByRecordedAtDesc(
                        Long.valueOf(req.getCanonicalId()), effectivePlatform)
                    .map(PriceRecord::getPrice)
                    .orElse(null);
            }
            unitPrice = retailPrice;
            currency  = "CNY";
            unit      = null;
        }

        BigDecimal totalAmount = (unitPrice != null)
            ? unitPrice.multiply(BigDecimal.valueOf(req.getQuantity())).setScale(2, RoundingMode.HALF_UP)
            : null;

        log.debug("B2B bulk price query: canonicalId={} platform={} quantity={} tierApplied={}",
            req.getCanonicalId(), req.getPlatform(), req.getQuantity(),
            matched != null ? matched.getId() : "none");

        return BulkPriceQueryResult.builder()
            .canonicalId(req.getCanonicalId())
            .platform(req.getPlatform())
            .quantity(req.getQuantity())
            .unitPrice(unitPrice)
            .totalAmount(totalAmount)
            .currency(currency)
            .unit(unit)
            .tierApplied(tierApplied)
            .allTiers(allTiers)
            .build();
    }

    /**
     * Create a bulk price tier. ADMIN only.
     * B2B scene: platform admins configure tiered pricing for B2B buyers.
     */
    @Transactional
    public BulkPriceTierDTO createBulkPriceTier(CreateBulkPriceTierRequest req) {
        BulkPriceTier tier = BulkPriceTier.builder()
            .canonicalId(req.getCanonicalId())
            .platform(req.getPlatform())
            .minQuantity(req.getMinQuantity())
            .maxQuantity(req.getMaxQuantity())
            .unitPrice(req.getUnitPrice())
            .currency(req.getCurrency() != null ? req.getCurrency() : "CNY")
            .unit(req.getUnit())
            .validFrom(req.getValidFrom())
            .validUntil(req.getValidUntil())
            .build();

        tier = bulkPriceTierRepository.save(tier);
        log.info("Created bulk price tier id={} canonicalId={} platform={} minQty={} unitPrice={}",
            tier.getId(), req.getCanonicalId(), req.getPlatform(),
            req.getMinQuantity(), req.getUnitPrice());

        // Invalidate cache for affected product/platform
        redisTemplate.delete(CACHE_BULK_TIERS_PREFIX + req.getCanonicalId() + ":" + req.getPlatform());
        redisTemplate.delete(CACHE_BULK_TIERS_PREFIX + req.getCanonicalId() + ":all");

        return toBulkTierDto(tier);
    }

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

    private PriceAlertDTO toDto(PriceAlert alert) {
        return PriceAlertDTO.builder()
            .id(alert.getId())
            .userId(alert.getUserId())
            .canonicalId(alert.getCanonicalId())
            .platform(alert.getPlatform())
            .targetPrice(alert.getTargetPrice())
            .triggered(alert.getTriggered())
            .createdAt(alert.getCreatedAt())
            .triggeredAt(alert.getTriggeredAt())
            .build();
    }

    private BulkPriceTierDTO toBulkTierDto(BulkPriceTier tier) {
        return BulkPriceTierDTO.builder()
            .canonicalId(tier.getCanonicalId())
            .platform(tier.getPlatform())
            .minQuantity(tier.getMinQuantity())
            .maxQuantity(tier.getMaxQuantity())
            .unitPrice(tier.getUnitPrice())
            .currency(tier.getCurrency())
            .unit(tier.getUnit())
            .validFrom(tier.getValidFrom())
            .validUntil(tier.getValidUntil())
            .build();
    }
}
