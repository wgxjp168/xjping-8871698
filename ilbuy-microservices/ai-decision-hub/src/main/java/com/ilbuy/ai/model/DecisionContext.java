package com.ilbuy.ai.model;

import jakarta.validation.constraints.NotBlank;

public record DecisionContext(
        @NotBlank(message = "决策类型不能为空")
        String decisionType,

        @NotBlank(message = "输入数据不能为空")
        String inputData,

        String userId,
        String sessionId
) {}
