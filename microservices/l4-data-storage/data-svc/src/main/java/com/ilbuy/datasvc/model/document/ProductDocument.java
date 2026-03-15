package com.ilbuy.datasvc.model.document;

import lombok.*;
import org.springframework.data.annotation.Id;
import org.springframework.data.elasticsearch.annotations.*;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * Elasticsearch 商品文档 (index: ilbuy_products)
 *
 * 映射策略：
 *  - title / title_cleaned: text (ik_max_word) + keyword (精确排序)
 *  - brand / platform:      keyword (facet/过滤)
 *  - price / score 字段:    double (数值范围过滤)
 */
@Document(indexName = "ilbuy_products", createIndex = true)
@Setting(settingPath = "es-settings.json")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ProductDocument {

    @Id
    private String canonicalId;

    @Field(type = FieldType.Keyword)
    private String platform;

    @Field(type = FieldType.Keyword)
    private String productId;

    @MultiField(
        mainField = @Field(type = FieldType.Text, analyzer = "ik_max_word", searchAnalyzer = "ik_smart"),
        otherFields = { @InnerField(suffix = "keyword", type = FieldType.Keyword) }
    )
    private String title;

    @MultiField(
        mainField = @Field(type = FieldType.Text, analyzer = "ik_max_word", searchAnalyzer = "ik_smart"),
        otherFields = { @InnerField(suffix = "keyword", type = FieldType.Keyword) }
    )
    private String titleCleaned;

    @Field(type = FieldType.Double)
    private BigDecimal price;

    @Field(type = FieldType.Double)
    private BigDecimal originalPrice;

    @Field(type = FieldType.Double)
    private Double discountPct;

    @Field(type = FieldType.Keyword)
    private String brandNormalised;

    @Field(type = FieldType.Keyword)
    private List<String> categoryPath;

    @Field(type = FieldType.Object, enabled = false)
    private Map<String, Object> specs;

    @Field(type = FieldType.Keyword, index = false)
    private List<String> images;

    @Field(type = FieldType.Integer)
    private Integer salesCount;

    @Field(type = FieldType.Integer)
    private Integer reviewCount;

    @Field(type = FieldType.Double)
    private Double averageRating;

    @Field(type = FieldType.Boolean)
    private Boolean inStock;

    @Field(type = FieldType.Integer)
    private Integer deliveryDays;

    @Field(type = FieldType.Keyword)
    private String shopName;

    @Field(type = FieldType.Boolean)
    private Boolean promotion;

    @Field(type = FieldType.Keyword, index = false)
    private String url;

    // ── 评分字段 ─────────────────────────────────────────────────
    @Field(type = FieldType.Double)
    private Double totalScore;

    @Field(type = FieldType.Keyword)
    private String grade;

    @Field(type = FieldType.Double)
    private Double priceScore;

    @Field(type = FieldType.Double)
    private Double popularityScore;

    @Field(type = FieldType.Double)
    private Double ratingScore;

    @Field(type = FieldType.Double)
    private Double availabilityScore;

    @Field(type = FieldType.Double)
    private Double valueForMoneyScore;

    @Field(type = FieldType.Double)
    private Double dataCompleteness;

    @Field(type = FieldType.Date, format = DateFormat.date_time)
    private Instant crawledAt;

    @Field(type = FieldType.Date, format = DateFormat.date_time)
    private Instant updatedAt;
}
