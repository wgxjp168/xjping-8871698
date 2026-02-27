package com.ilbuy.ai.service;

import com.ilbuy.ai.model.PricingRequest;
import com.ilbuy.ai.model.PricingResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class PricingService {

    private static final Logger log = LoggerFactory.getLogger(PricingService.class);

    public PricingResult calculatePrice(PricingRequest request) {
        log.info("智能定价: productId={}, basePrice={}, stock={}, demand={}",
                request.productId(), request.basePrice(),
                request.stockQuantity(), request.demandLevel());

        double factor = 1.0;
        String strategy;
        String explanation;

        if (request.demandLevel() > 8) {
            factor = 1.05;
            strategy = "high-demand-premium";
            explanation = "需求旺盛，建议适当上调价格";
        } else if (request.stockQuantity() > 1000) {
            factor = 0.90;
            strategy = "overstock-clearance";
            explanation = "库存充足，建议降价促销加速周转";
        } else if (request.demandLevel() < 3 && request.stockQuantity() > 500) {
            factor = 0.85;
            strategy = "low-demand-discount";
            explanation = "需求较低且库存偏高，建议折扣清仓";
        } else {
            strategy = "stable-pricing";
            explanation = "供需平衡，建议维持当前价格";
        }

        double suggestedPrice = Math.round(request.basePrice() * factor * 100.0) / 100.0;
        double discount = Math.round((1 - factor) * 10000.0) / 100.0;

        return new PricingResult(
                request.productId(),
                request.basePrice(),
                suggestedPrice,
                discount,
                strategy,
                explanation
        );
    }
}
