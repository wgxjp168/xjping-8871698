package com.ilbuy.datasvc.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ilbuy.datasvc.model.dto.IngestRequest;
import com.ilbuy.datasvc.model.dto.IngestResponse;
import com.ilbuy.datasvc.model.dto.ProductIngestDTO;
import com.ilbuy.datasvc.model.entity.PriceHistory;
import com.ilbuy.datasvc.model.entity.Product;
import com.ilbuy.datasvc.mq.producer.IngestProducer;
import com.ilbuy.datasvc.repository.mysql.PriceHistoryRepository;
import com.ilbuy.datasvc.repository.mysql.ProductRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 核心写入编排服务
 *
 * 数据流：
 *   POST /ingest → IngestService.ingest()
 *     ├── 1. MySQL upsert (主存储，同步)
 *     ├── 2. PriceHistory append
 *     ├── 3. Redis 热数据缓存 (同步)
 *     └── 4. RabbitMQ 发送 → 消费者异步写入 ES + ClickHouse
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class IngestService {

    private final ProductRepository      productRepository;
    private final PriceHistoryRepository priceHistoryRepository;
    private final CacheService           cacheService;
    private final IngestProducer         ingestProducer;
    private final ObjectMapper           objectMapper;

    @Transactional
    public IngestResponse ingest(IngestRequest request) {
        long t0 = System.currentTimeMillis();
        AtomicInteger saved  = new AtomicInteger();
        AtomicInteger failed = new AtomicInteger();

        List<ProductIngestDTO> toQueue = new ArrayList<>();

        for (ProductIngestDTO dto : request.getProducts()) {
            try {
                upsertToMySQL(dto);
                cacheService.cacheProduct(dto);
                toQueue.add(dto);
                saved.incrementAndGet();
            } catch (Exception e) {
                log.error("Ingest failed for canonicalId={}: {}", dto.getCanonicalId(), e.getMessage());
                failed.incrementAndGet();
            }
        }

        // 批量异步推送 RabbitMQ → ES + ClickHouse
        toQueue.forEach(ingestProducer::sendToEsQueue);
        toQueue.forEach(ingestProducer::sendToAnalyticsQueue);

        long duration = System.currentTimeMillis() - t0;
        log.info("\"Ingest job={} session={} total={} saved={} failed={} duration={}ms\"",
            request.getJobId(), request.getSessionId(),
            request.getProducts().size(), saved.get(), failed.get(), duration);

        return IngestResponse.builder()
            .jobId(request.getJobId())
            .sessionId(request.getSessionId())
            .total(request.getProducts().size())
            .saved(saved.get())
            .failed(failed.get())
            .durationMs(duration)
            .processedAt(Instant.now())
            .status(failed.get() == 0 ? "success" : "partial")
            .build();
    }

    // ── MySQL upsert ──────────────────────────────────────────────────

    private void upsertToMySQL(ProductIngestDTO dto) {
        Product existing = productRepository.findByCanonicalId(dto.getCanonicalId()).orElse(null);

        if (existing == null) {
            productRepository.save(toEntity(dto));
        } else {
            // 只更新变化字段
            updateEntity(existing, dto);
            productRepository.save(existing);
        }

        // 每次入库追加价格历史
        priceHistoryRepository.save(PriceHistory.builder()
            .canonicalId(dto.getCanonicalId())
            .price(dto.getPrice())
            .originalPrice(dto.getOriginalPrice())
            .totalScore(dto.getTotalScore())
            .build());
    }

    private Product toEntity(ProductIngestDTO dto) {
        return Product.builder()
            .canonicalId(dto.getCanonicalId())
            .platform(dto.getPlatform())
            .productId(dto.getProductId())
            .title(dto.getTitle())
            .titleCleaned(dto.getTitleCleaned())
            .price(dto.getPrice())
            .originalPrice(dto.getOriginalPrice())
            .discountPct(dto.getDiscountPct())
            .brandNormalised(dto.getBrandNormalised())
            .categoryPath(toJson(dto.getCategoryPath()))
            .specs(toJson(dto.getSpecs()))
            .images(toJson(dto.getImages()))
            .salesCount(dto.getSalesCount())
            .reviewCount(dto.getReviewCount())
            .averageRating(dto.getAverageRating())
            .inStock(dto.getInStock())
            .deliveryDays(dto.getDeliveryDays())
            .shopName(dto.getShopName())
            .promotion(dto.getPromotion())
            .url(dto.getUrl())
            .totalScore(dto.getTotalScore())
            .grade(dto.getGrade())
            .priceScore(dto.getPriceScore())
            .popularityScore(dto.getPopularityScore())
            .ratingScore(dto.getRatingScore())
            .availabilityScore(dto.getAvailabilityScore())
            .valueForMoneyScore(dto.getValueForMoneyScore())
            .dataCompleteness(dto.getDataCompleteness())
            .dedupeKey(dto.getDedupeKey())
            .isMock(dto.getIsMock())
            .crawledAt(parseInstant(dto.getCrawledAt()))
            .build();
    }

    private void updateEntity(Product p, ProductIngestDTO dto) {
        p.setPrice(dto.getPrice());
        p.setOriginalPrice(dto.getOriginalPrice());
        p.setDiscountPct(dto.getDiscountPct());
        p.setSalesCount(dto.getSalesCount());
        p.setReviewCount(dto.getReviewCount());
        p.setAverageRating(dto.getAverageRating());
        p.setInStock(dto.getInStock());
        p.setPromotion(dto.getPromotion());
        p.setTotalScore(dto.getTotalScore());
        p.setGrade(dto.getGrade());
        p.setPriceScore(dto.getPriceScore());
        p.setPopularityScore(dto.getPopularityScore());
        p.setRatingScore(dto.getRatingScore());
        p.setAvailabilityScore(dto.getAvailabilityScore());
        p.setValueForMoneyScore(dto.getValueForMoneyScore());
        p.setCrawledAt(parseInstant(dto.getCrawledAt()));
    }

    private String toJson(Object obj) {
        if (obj == null) return null;
        try {
            return objectMapper.writeValueAsString(obj);
        } catch (Exception e) {
            return "[]";
        }
    }

    private Instant parseInstant(String ts) {
        try {
            return ts != null ? Instant.parse(ts) : Instant.now();
        } catch (Exception e) {
            return Instant.now();
        }
    }
}
