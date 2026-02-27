package com.ilbuy.ai.service;

import com.ilbuy.ai.model.ProductRecommendation;
import com.ilbuy.ai.model.RecommendationRequest;
import com.ilbuy.ai.model.RecommendationResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

@Service
public class RecommendationService {

    private static final Logger log = LoggerFactory.getLogger(RecommendationService.class);
    private static final Random random = new Random();

    private static final String[][] SAMPLE_PRODUCTS = {
            {"P001", "智能手表Pro", "electronics", "1299.00"},
            {"P002", "无线降噪耳机", "electronics", "899.00"},
            {"P003", "运动跑鞋", "sports", "599.00"},
            {"P004", "有机绿茶礼盒", "food", "168.00"},
            {"P005", "便携充电宝20000mAh", "electronics", "199.00"},
            {"P006", "纯棉T恤", "clothing", "89.00"},
            {"P007", "智能台灯", "home", "259.00"},
            {"P008", "蓝牙音箱", "electronics", "349.00"},
            {"P009", "瑜伽垫", "sports", "129.00"},
            {"P010", "保温杯", "home", "79.00"},
    };

    private static final String[] REASONS = {
            "根据您的浏览历史推荐",
            "与您购买过的商品相似",
            "同类用户热门选择",
            "当季热销商品",
            "AI算法个性化推荐",
            "基于您的收藏偏好"
    };

    public RecommendationResult recommend(RecommendationRequest request) {
        long start = System.currentTimeMillis();
        log.info("生成推荐: userId={}, category={}, limit={}",
                request.userId(), request.category(), request.limit());

        List<ProductRecommendation> recommendations = new ArrayList<>();
        int count = Math.min(request.limit(), SAMPLE_PRODUCTS.length);

        for (int i = 0; i < count; i++) {
            String[] p = SAMPLE_PRODUCTS[i];
            if (request.category() != null && !request.category().isEmpty()
                    && !p[2].equalsIgnoreCase(request.category())) {
                continue;
            }
            recommendations.add(new ProductRecommendation(
                    p[0], p[1], p[2],
                    Double.parseDouble(p[3]),
                    0.95 - (i * 0.05) + random.nextDouble() * 0.03,
                    REASONS[random.nextInt(REASONS.length)]
            ));
        }

        long duration = System.currentTimeMillis() - start;
        String strategy = request.category() != null && !request.category().isEmpty()
                ? "category-filtered-collaborative" : "hybrid-collaborative-filtering";

        return new RecommendationResult(request.userId(), strategy, recommendations, duration);
    }
}
