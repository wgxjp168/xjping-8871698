package com.ilbuy.price.service;

import com.ilbuy.price.dto.*;
import com.ilbuy.price.model.entity.PriceAlert;
import com.ilbuy.price.model.entity.PriceRecord;
import com.ilbuy.price.model.entity.PriceTrend;
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
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class PriceService {

    private static final String CACHE_HISTORY_PREFIX = "price:history:";
    private static final String CACHE_TREND_PREFIX   = "price:trend:";
    private static final String CACHE_COMPARE_PREFIX = "price:compare:";

    private final PriceRecordRepository priceRecordRepository;
    private final PriceAlertRepository  priceAlertRepository;
    private final PriceTrendRepository  priceTrendRepository;
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
}
