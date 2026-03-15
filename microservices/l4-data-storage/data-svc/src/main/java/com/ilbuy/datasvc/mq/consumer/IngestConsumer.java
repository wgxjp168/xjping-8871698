package com.ilbuy.datasvc.mq.consumer;

import com.ilbuy.datasvc.model.document.ProductDocument;
import com.ilbuy.datasvc.model.dto.ProductIngestDTO;
import com.ilbuy.datasvc.mq.config.RabbitMQConfig;
import com.ilbuy.datasvc.repository.es.ProductEsRepository;
import com.ilbuy.datasvc.service.AnalyticsService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.List;

/**
 * RabbitMQ 消费者
 *
 * ES 队列消费者：  将商品数据写入 Elasticsearch
 * 分析队列消费者：将商品数据写入 ClickHouse（通过 AnalyticsService）
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class IngestConsumer {

    private final ProductEsRepository esRepository;
    private final AnalyticsService    analyticsService;

    // ── ES 消费者 ─────────────────────────────────────────────────────

    @RabbitListener(
        queues = RabbitMQConfig.Q_ES,
        containerFactory = "rabbitListenerContainerFactory"
    )
    public void consumeEsQueue(ProductIngestDTO dto) {
        try {
            esRepository.save(toDocument(dto));
            log.debug("ES indexed: canonicalId={}", dto.getCanonicalId());
        } catch (Exception e) {
            log.error("ES index failed canonicalId={}: {}", dto.getCanonicalId(), e.getMessage());
            throw e;   // 触发重试，最终到 DLQ
        }
    }

    // ── Analytics 消费者 ──────────────────────────────────────────────

    @RabbitListener(
        queues = RabbitMQConfig.Q_ANALYTICS,
        containerFactory = "rabbitListenerContainerFactory"
    )
    public void consumeAnalyticsQueue(ProductIngestDTO dto) {
        try {
            analyticsService.writeToClickHouse(dto);
            log.debug("ClickHouse written: canonicalId={}", dto.getCanonicalId());
        } catch (Exception e) {
            log.error("ClickHouse write failed canonicalId={}: {}", dto.getCanonicalId(), e.getMessage());
            throw e;
        }
    }

    // ── Converter ─────────────────────────────────────────────────────

    private ProductDocument toDocument(ProductIngestDTO dto) {
        return ProductDocument.builder()
            .canonicalId(dto.getCanonicalId())
            .platform(dto.getPlatform())
            .productId(dto.getProductId())
            .title(dto.getTitle())
            .titleCleaned(dto.getTitleCleaned())
            .price(dto.getPrice())
            .originalPrice(dto.getOriginalPrice())
            .discountPct(dto.getDiscountPct())
            .brandNormalised(dto.getBrandNormalised())
            .categoryPath(dto.getCategoryPath())
            .specs(dto.getSpecs())
            .images(dto.getImages())
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
            .crawledAt(parseInstant(dto.getCrawledAt()))
            .updatedAt(Instant.now())
            .build();
    }

    private Instant parseInstant(String ts) {
        try { return ts != null ? Instant.parse(ts) : Instant.now(); }
        catch (Exception e) { return Instant.now(); }
    }
}
