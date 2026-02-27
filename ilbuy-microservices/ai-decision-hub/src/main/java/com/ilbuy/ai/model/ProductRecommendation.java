package com.ilbuy.ai.model;

public record ProductRecommendation(
        String productId,
        String productName,
        String category,
        double price,
        double score,
        String reason
) {}
