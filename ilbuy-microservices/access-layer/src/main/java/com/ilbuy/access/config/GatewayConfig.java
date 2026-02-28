package com.ilbuy.access.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.gateway.route.RouteLocator;
import org.springframework.cloud.gateway.route.builder.RouteLocatorBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class GatewayConfig {

    @Value("${ilbuy.routes.business-logic:http://business-logic:8082}")
    private String businessLogicUrl;

    @Value("${ilbuy.routes.ai-decision-hub:http://ai-decision-hub:8081}")
    private String aiDecisionHubUrl;

    @Value("${ilbuy.routes.data-layer:http://data-layer:8083}")
    private String dataLayerUrl;

    @Value("${ilbuy.routes.support-ops:http://support-ops:8084}")
    private String supportOpsUrl;

    @Bean
    public RouteLocator customRouteLocator(RouteLocatorBuilder builder) {
        return builder.routes()
                // 业务逻辑层
                .route("user-service", r -> r.path("/api/users/**").uri(businessLogicUrl))
                .route("product-service", r -> r.path("/api/products/**").uri(businessLogicUrl))
                .route("order-service", r -> r.path("/api/orders/**").uri(businessLogicUrl))
                .route("cart-service", r -> r.path("/api/cart/**").uri(businessLogicUrl))
                .route("business-status", r -> r.path("/api/status").uri(businessLogicUrl))
                // AI 决策中枢
                .route("ai-service", r -> r.path("/api/ai/**").uri(aiDecisionHubUrl))
                // 数据层
                .route("data-service", r -> r.path("/api/data/**").uri(dataLayerUrl))
                // 支撑运维层
                .route("ops-service", r -> r.path("/api/ops/**").uri(supportOpsUrl))
                .build();
    }
}
