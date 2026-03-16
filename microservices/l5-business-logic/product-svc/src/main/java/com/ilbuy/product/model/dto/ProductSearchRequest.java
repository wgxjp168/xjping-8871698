package com.ilbuy.product.model.dto;

import lombok.Data;

@Data
public class ProductSearchRequest {

    /** Full-text keyword (searches name, description, tags) */
    private String keyword;

    /** Filter by category */
    private Long categoryId;

    /** Minimum price filter (inclusive) */
    private java.math.BigDecimal minPrice;

    /** Maximum price filter (inclusive) */
    private java.math.BigDecimal maxPrice;

    /** Filter by platform (jd / taobao / pdd) */
    private String platform;

    /** Zero-based page number */
    private int page = 0;

    /** Page size */
    private int size = 20;

    /**
     * Sort field: "price_asc", "price_desc", "newest", "relevance".
     * Defaults to "relevance".
     */
    private String sortBy = "relevance";
}
