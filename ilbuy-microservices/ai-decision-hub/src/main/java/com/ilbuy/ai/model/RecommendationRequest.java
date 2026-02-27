package com.ilbuy.ai.model;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

public record RecommendationRequest(
        @NotBlank(message = "用户ID不能为空")
        String userId,

        String category,

        @Min(value = 1, message = "推荐数量最少为1")
        @Max(value = 50, message = "推荐数量最多为50")
        int limit
) {
    public RecommendationRequest {
        if (limit == 0) limit = 10;
    }
}
