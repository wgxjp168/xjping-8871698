package com.ilbuy.datasvc.model.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.math.BigDecimal;

/**
 * L5 业务层商品搜索请求（预留）
 */
@Data
public class SearchRequest {

    @NotBlank
    private String keyword;

    private String platform;

    private String brand;

    private BigDecimal priceMin;

    private BigDecimal priceMax;

    private String grade;        // A/B/C/D

    private Double minRating;

    private Boolean inStockOnly;

    private String sortBy;       // total_score / price / review_count / crawled_at

    private String sortOrder;    // asc / desc

    @Min(0)
    private int page = 0;

    @Min(1) @Max(100)
    private int size = 20;
}
