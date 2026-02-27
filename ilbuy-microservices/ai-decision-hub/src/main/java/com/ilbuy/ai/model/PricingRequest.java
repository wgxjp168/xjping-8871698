package com.ilbuy.ai.model;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;

public record PricingRequest(
        @NotBlank(message = "商品ID不能为空")
        String productId,

        @Positive(message = "基础价格必须大于0")
        double basePrice,

        String category,
        int stockQuantity,
        int demandLevel
) {}
