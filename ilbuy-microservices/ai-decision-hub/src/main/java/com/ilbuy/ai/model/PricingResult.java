package com.ilbuy.ai.model;

public record PricingResult(
        String productId,
        double basePrice,
        double suggestedPrice,
        double discount,
        String strategy,
        String explanation
) {}
