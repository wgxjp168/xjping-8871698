package com.ilbuy.gateway.api.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.ilbuy.gateway.api.properties.JwtGatewayProperties;
import com.ilbuy.gateway.api.ratelimit.IpKeyResolver;
import com.ilbuy.gateway.api.ratelimit.UserKeyResolver;
import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver;
import org.springframework.cloud.gateway.filter.ratelimit.RedisRateLimiter;
import org.springframework.cloud.gateway.route.RouteLocator;
import org.springframework.cloud.gateway.route.builder.RouteLocatorBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

/**
 * API 网关核心配置：路由 / 限流 Key 解析器 / 公共 Bean
 *
 * <p>路由设计：
 * <table border="1">
 *   <tr><th>路由 ID</th><th>匹配路径</th><th>下游服务</th><th>限流策略</th></tr>
 *   <tr><td>dialog-route</td><td>/api/v1/dialog/**</td><td>lb://dialog-service</td><td>C端 用户维度</td></tr>
 *   <tr><td>order-route</td><td>/api/v1/order/**</td><td>lb://order-service</td><td>C端 用户维度</td></tr>
 *   <tr><td>user-route</td><td>/api/v1/user/**</td><td>lb://user-service</td><td>C端 用户维度</td></tr>
 *   <tr><td>product-route</td><td>/api/v1/product/**</td><td>lb://product-service</td><td>C端 用户维度</td></tr>
 *   <tr><td>b-api-route</td><td>/api/v1/open/**</td><td>lb://open-api-service</td><td>B端 IP 维度</td></tr>
 * </table>
 * </p>
 */
@Configuration
public class GatewayConfig {

    // ═══════════════════════ 限流 Key 解析器 Bean ═══════════════════════

    /**
     * C端用户限流 Key 解析器（userId > X-User-Id > clientIP）
     */
    @Bean
    @Primary
    public KeyResolver userKeyResolver(JwtGatewayProperties jwtProperties) {
        return new UserKeyResolver(jwtProperties.getSecret());
    }

    /**
     * B端 IP 限流 Key 解析器
     */
    @Bean
    public KeyResolver ipKeyResolver() {
        return new IpKeyResolver();
    }

    // ═══════════════════════ Redis 限流器 ═══════════════════════

    /**
     * C端限流：100 请求/分钟（replenishRate=2, burstCapacity=5，令牌桶算法）
     *
     * <p>Spring Cloud Gateway 使用令牌桶，replenishRate 为每秒补充速率。
     * 100/min ≈ 1.67/s，取 replenishRate=2，burstCapacity=5 允许短时突发。</p>
     */
    @Bean
    public RedisRateLimiter consumerRateLimiter() {
        return new RedisRateLimiter(2, 5, 1);  // replenishRate, burstCapacity, requestedTokens
    }

    /**
     * B端 API 限流：1000 请求/分钟（replenishRate=17, burstCapacity=50）
     */
    @Bean
    public RedisRateLimiter bApiRateLimiter() {
        return new RedisRateLimiter(17, 50, 1);
    }

    // ═══════════════════════ 路由定义 ═══════════════════════

    @Bean
    public RouteLocator routeLocator(RouteLocatorBuilder builder,
                                     RedisRateLimiter consumerRateLimiter,
                                     RedisRateLimiter bApiRateLimiter,
                                     KeyResolver userKeyResolver,
                                     KeyResolver ipKeyResolver) {
        return builder.routes()

            // ── 对话服务（C端核心，限流最严）──
            // 熔断由 SentinelGatewayFilter（GlobalFilter）统一处理，此处只配置限流
            .route("dialog-route", r -> r
                .path("/api/v1/dialog/**")
                .filters(f -> f
                    .rewritePath("/api/v1/dialog/(?<seg>.*)", "/${seg}")
                    .addRequestHeader("X-Downstream-Service", "dialog-service")
                    .requestRateLimiter(c -> c
                        .setRateLimiter(consumerRateLimiter)
                        .setKeyResolver(userKeyResolver)
                        .setDenyEmptyKey(false)))
                .uri("lb://dialog-service"))

            // ── 订单服务 ──
            .route("order-route", r -> r
                .path("/api/v1/order/**")
                .filters(f -> f
                    .rewritePath("/api/v1/order/(?<seg>.*)", "/${seg}")
                    .addRequestHeader("X-Downstream-Service", "order-service")
                    .requestRateLimiter(c -> c
                        .setRateLimiter(consumerRateLimiter)
                        .setKeyResolver(userKeyResolver)
                        .setDenyEmptyKey(false)))
                .uri("lb://order-service"))

            // ── 用户服务 ──
            .route("user-route", r -> r
                .path("/api/v1/user/**")
                .filters(f -> f
                    .rewritePath("/api/v1/user/(?<seg>.*)", "/${seg}")
                    .requestRateLimiter(c -> c
                        .setRateLimiter(consumerRateLimiter)
                        .setKeyResolver(userKeyResolver)
                        .setDenyEmptyKey(false)))
                .uri("lb://user-service"))

            // ── 商品服务 ──
            .route("product-route", r -> r
                .path("/api/v1/product/**")
                .filters(f -> f
                    .rewritePath("/api/v1/product/(?<seg>.*)", "/${seg}")
                    .requestRateLimiter(c -> c
                        .setRateLimiter(consumerRateLimiter)
                        .setKeyResolver(userKeyResolver)
                        .setDenyEmptyKey(false)))
                .uri("lb://product-service"))

            // ── B端开放 API（IP 维度限流，1000/min）──
            .route("b-api-route", r -> r
                .path("/api/v1/open/**")
                .filters(f -> f
                    .rewritePath("/api/v1/open/(?<seg>.*)", "/${seg}")
                    .addRequestHeader("X-Api-Type", "B-END")
                    .requestRateLimiter(c -> c
                        .setRateLimiter(bApiRateLimiter)
                        .setKeyResolver(ipKeyResolver)
                        .setDenyEmptyKey(false)))
                .uri("lb://open-api-service"))

            // ── 认证服务（白名单，不限流）──
            .route("auth-route", r -> r
                .path("/api/v1/auth/**")
                .filters(f -> f
                    .rewritePath("/api/v1/auth/(?<seg>.*)", "/${seg}"))
                .uri("lb://auth-service"))

            .build();
    }

    // ═══════════════════════ Jackson ═══════════════════════

    @Bean
    public ObjectMapper objectMapper() {
        ObjectMapper om = new ObjectMapper();
        om.registerModule(new JavaTimeModule());
        om.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        return om;
    }
}
