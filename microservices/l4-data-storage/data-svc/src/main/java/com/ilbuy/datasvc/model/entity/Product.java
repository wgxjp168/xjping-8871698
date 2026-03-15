package com.ilbuy.datasvc.model.entity;

import jakarta.persistence.*;
import lombok.*;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

/**
 * 商品主表 JPA 实体 (MySQL)
 * canonical_id 作为跨平台唯一标识
 */
@Entity
@Table(
    name = "products",
    indexes = {
        @Index(name = "idx_canonical_id",  columnList = "canonical_id", unique = true),
        @Index(name = "idx_platform_pid",  columnList = "platform, product_id"),
        @Index(name = "idx_brand",         columnList = "brand_normalised"),
        @Index(name = "idx_total_score",   columnList = "total_score"),
        @Index(name = "idx_crawled_at",    columnList = "crawled_at"),
    }
)
@EntityListeners(AuditingEntityListener.class)
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Product {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "canonical_id", nullable = false, length = 64, unique = true)
    private String canonicalId;

    @Column(nullable = false, length = 32)
    private String platform;

    @Column(name = "product_id", nullable = false, length = 128)
    private String productId;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String title;

    @Column(name = "title_cleaned", columnDefinition = "TEXT")
    private String titleCleaned;

    @Column(nullable = false, precision = 12, scale = 2)
    private BigDecimal price;

    @Column(name = "original_price", precision = 12, scale = 2)
    private BigDecimal originalPrice;

    @Column(name = "discount_pct")
    private Double discountPct;

    @Column(name = "brand_normalised", length = 128)
    private String brandNormalised;

    /** 存为 JSON 字符串，如 ["数码","手机","智能手机"] */
    @Column(name = "category_path", columnDefinition = "JSON")
    private String categoryPath;

    /** 规格 JSON，如 {"颜色":"黑色","存储":"256GB"} */
    @Column(columnDefinition = "JSON")
    private String specs;

    /** 图片 URL 列表 JSON */
    @Column(columnDefinition = "JSON")
    private String images;

    @Column(name = "sales_count")
    private Integer salesCount;

    @Column(name = "review_count")
    private Integer reviewCount;

    @Column(name = "average_rating")
    private Double averageRating;

    @Column(name = "in_stock")
    private Boolean inStock;

    @Column(name = "delivery_days")
    private Integer deliveryDays;

    @Column(name = "shop_name", length = 256)
    private String shopName;

    private Boolean promotion;

    @Column(length = 512)
    private String url;

    // ── 评分字段 ──────────────────────────────────────────────────
    @Column(name = "total_score")
    private Double totalScore;

    @Column(length = 2)
    private String grade;

    @Column(name = "price_score")
    private Double priceScore;

    @Column(name = "popularity_score")
    private Double popularityScore;

    @Column(name = "rating_score")
    private Double ratingScore;

    @Column(name = "availability_score")
    private Double availabilityScore;

    @Column(name = "value_for_money_score")
    private Double valueForMoneyScore;

    @Column(name = "data_completeness")
    private Double dataCompleteness;

    @Column(name = "dedupe_key", length = 64)
    private String dedupeKey;

    @Column(name = "is_mock")
    private Boolean isMock;

    @Column(name = "crawled_at")
    private Instant crawledAt;

    @CreatedDate
    @Column(name = "created_at", updatable = false)
    private Instant createdAt;

    @LastModifiedDate
    @Column(name = "updated_at")
    private Instant updatedAt;
}
