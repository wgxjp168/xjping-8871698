package com.ilbuy.flink.model;

import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.math.BigDecimal;

/** Flink 流中传递的商品事件（与 data-svc ProductIngestDTO 对齐） */
@Data
@NoArgsConstructor
public class ProductEvent implements Serializable {
    private static final long serialVersionUID = 1L;

    private String canonicalId;
    private String platform;
    private String productId;
    private String titleCleaned;
    private String brandNormalised;
    private BigDecimal price;
    private BigDecimal originalPrice;
    private Double discountPct;
    private Double totalScore;
    private String grade;
    private Double priceScore;
    private Double popularityScore;
    private Double ratingScore;
    private Double availabilityScore;
    private Double valueForMoneyScore;
    private Integer salesCount;
    private Integer reviewCount;
    private Double averageRating;
    private Boolean inStock;
    private Boolean isMock;
    private String crawledAt;

    // ── Flink 流处理附加字段 ────────────────────────────────────────
    private Long processedAt;      // 流处理时间戳（毫秒）
    private String scorePercentile; // 分位数标签（TOP10/TOP25/REST）
}
