package com.ilbuy.ai.service;

import com.ilbuy.ai.model.DecisionContext;
import com.ilbuy.ai.model.DecisionResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;

@Service
public class DecisionService {

    private static final Logger log = LoggerFactory.getLogger(DecisionService.class);

    public DecisionResult makeDecision(DecisionContext context) {
        log.info("AI决策: type={}, userId={}, sessionId={}",
                context.decisionType(), context.userId(), context.sessionId());

        String decisionId = UUID.randomUUID().toString().substring(0, 12);

        return switch (context.decisionType().toLowerCase()) {
            case "purchase_intent" -> analyzePurchaseIntent(decisionId, context);
            case "fraud_detection" -> detectFraud(decisionId, context);
            case "user_segment" -> segmentUser(decisionId, context);
            default -> new DecisionResult(
                    decisionId,
                    context.decisionType(),
                    "processed",
                    0.75,
                    Map.of("input", context.inputData(), "note", "通用决策处理"),
                    LocalDateTime.now()
            );
        };
    }

    private DecisionResult analyzePurchaseIntent(String id, DecisionContext ctx) {
        return new DecisionResult(id, "purchase_intent", "high_intent", 0.87,
                Map.of(
                        "intent_level", "high",
                        "suggested_action", "推送优惠券促进转化",
                        "conversion_probability", 0.72
                ),
                LocalDateTime.now());
    }

    private DecisionResult detectFraud(String id, DecisionContext ctx) {
        return new DecisionResult(id, "fraud_detection", "safe", 0.95,
                Map.of(
                        "risk_level", "low",
                        "risk_score", 0.05,
                        "check_items", "设备指纹|IP地理位置|行为模式"
                ),
                LocalDateTime.now());
    }

    private DecisionResult segmentUser(String id, DecisionContext ctx) {
        return new DecisionResult(id, "user_segment", "premium_shopper", 0.82,
                Map.of(
                        "segment", "高价值用户",
                        "lifetime_value", "high",
                        "preferred_categories", "electronics,home"
                ),
                LocalDateTime.now());
    }
}
