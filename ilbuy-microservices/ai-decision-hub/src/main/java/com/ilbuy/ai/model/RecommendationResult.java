package com.ilbuy.ai.model;

import java.util.List;

public record RecommendationResult(
        String userId,
        String strategy,
        List<ProductRecommendation> recommendations,
        long processingTimeMs
) {}
