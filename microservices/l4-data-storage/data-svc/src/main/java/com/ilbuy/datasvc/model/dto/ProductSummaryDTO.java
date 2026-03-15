package com.ilbuy.datasvc.model.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

/** 搜索结果列表项 */
@Data
public class ProductSummaryDTO {
    private String canonicalId;
    private String platform;
    private String title;
    private BigDecimal price;
    private BigDecimal originalPrice;
    private Double discountPct;
    private String brand;
    private String grade;
    private Double totalScore;
    private Double averageRating;
    private Integer reviewCount;
    private Boolean inStock;
    private String thumbnailUrl;
    private String url;
    private String crawledAt;
}
