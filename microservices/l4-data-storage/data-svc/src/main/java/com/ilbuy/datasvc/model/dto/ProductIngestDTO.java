package com.ilbuy.datasvc.model.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import lombok.Data;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * 单个清洗后商品数据 DTO（来自 L3 CleanProduct）
 */
@Data
public class ProductIngestDTO {

    @NotBlank
    @JsonProperty("canonical_id")
    private String canonicalId;

    @NotBlank
    private String platform;

    @NotBlank
    @JsonProperty("product_id")
    private String productId;

    @NotBlank
    private String title;

    @JsonProperty("title_cleaned")
    private String titleCleaned;

    @NotNull
    @PositiveOrZero
    private BigDecimal price;

    @JsonProperty("original_price")
    private BigDecimal originalPrice;

    @JsonProperty("discount_pct")
    private Double discountPct;

    @JsonProperty("brand_normalised")
    private String brandNormalised;

    @JsonProperty("category_path")
    private List<String> categoryPath;

    private Map<String, Object> specs;

    private List<String> images;

    @JsonProperty("sales_count")
    private Integer salesCount;

    @JsonProperty("review_count")
    private Integer reviewCount;

    @JsonProperty("average_rating")
    private Double averageRating;

    @JsonProperty("in_stock")
    private Boolean inStock;

    @JsonProperty("delivery_days")
    private Integer deliveryDays;

    @JsonProperty("shop_name")
    private String shopName;

    private Boolean promotion;

    private String url;

    // ── 评分字段（来自 Scorer）──────────────────────────────────
    @JsonProperty("total_score")
    private Double totalScore;

    @JsonProperty("grade")
    private String grade;

    @JsonProperty("price_score")
    private Double priceScore;

    @JsonProperty("popularity_score")
    private Double popularityScore;

    @JsonProperty("rating_score")
    private Double ratingScore;

    @JsonProperty("availability_score")
    private Double availabilityScore;

    @JsonProperty("value_for_money_score")
    private Double valueForMoneyScore;

    @JsonProperty("data_completeness")
    private Double dataCompleteness;

    @JsonProperty("dedupe_key")
    private String dedupeKey;

    @JsonProperty("is_mock")
    private Boolean isMock;

    @JsonProperty("crawled_at")
    private String crawledAt;
}
