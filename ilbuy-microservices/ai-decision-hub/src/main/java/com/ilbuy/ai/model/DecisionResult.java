package com.ilbuy.ai.model;

import java.time.LocalDateTime;
import java.util.Map;

public record DecisionResult(
        String decisionId,
        String decisionType,
        String outcome,
        double confidence,
        Map<String, Object> details,
        LocalDateTime timestamp
) {}
