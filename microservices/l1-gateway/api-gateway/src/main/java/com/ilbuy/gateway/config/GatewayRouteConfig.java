package com.ilbuy.gateway.config;

import org.springframework.cloud.gateway.route.RouteLocator;
import org.springframework.cloud.gateway.route.builder.RouteLocatorBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

/**
 * Gateway 路由配置（Java DSL 方式，与 application.yml 路由互补）
 *
 * <p>数据流转：
 * <pre>
 *   L0 INPUT_MODES
 *     TEXT_IN / VOICE_IN  ──→  /api/v1/input/**   → multimodal-input-svc
 *     USER_PROFILE        ──→  /api/v1/profile/**  → user-profile-svc
 *   L1 SELF
 *     AUTH                ──→  /auth/**            → auth-svc (port 8001)
 *     WS                  ──→  /ws/**              → websocket-svc
 *   L2 预留（对话管理）
 *     CHAT                ──→  /api/v1/chat/**     → conversation-svc (L2)
 *   L5 业务逻辑
 *     USER                ──→  /api/v1/user/**     → user-svc
 * </pre>
 */
@Configuration
public class GatewayRouteConfig {

    @Bean
    public RouteLocator customRouteLocator(RouteLocatorBuilder builder) {
        return builder.routes()

            // ============ L1: 认证服务（不经过JWT鉴权过滤器）============
            .route("auth-svc", r -> r
                .path("/auth/**")
                .filters(f -> f
                    .rewritePath("/auth/(?<segment>.*)", "/auth/${segment}")
                    .circuitBreaker(c -> c
                        .setName("auth-cb")
                        .setFallbackUri("forward:/fallback/auth"))
                    .retry(config -> config
                        .setRetries(2)
                        .setBackoff(Duration.ofMillis(100), Duration.ofMillis(500), 2, true)))
                .uri("lb://auth-svc"))

            // ============ L1: WebSocket 实时会话服务 ============
            .route("websocket-svc", r -> r
                .path("/ws/**")
                .filters(f -> f
                    .rewritePath("/ws/(?<segment>.*)", "/ws/${segment}"))
                .uri("lb://websocket-svc"))

            // ============ L0: 多模态输入服务 ============
            .route("multimodal-input-svc", r -> r
                .path("/api/v1/input/**")
                .filters(f -> f
                    .rewritePath("/api/v1/input/(?<segment>.*)", "/api/v1/input/${segment}")
                    .circuitBreaker(c -> c
                        .setName("multimodal-cb")
                        .setFallbackUri("forward:/fallback/input")))
                .uri("lb://multimodal-input-svc"))

            // ============ L0: 用户画像服务 ============
            .route("user-profile-svc", r -> r
                .path("/api/v1/profile/**")
                .filters(f -> f
                    .rewritePath("/api/v1/profile/(?<segment>.*)", "/api/v1/profile/${segment}")
                    .circuitBreaker(c -> c
                        .setName("profile-cb")
                        .setFallbackUri("forward:/fallback/generic")))
                .uri("lb://user-profile-svc"))

            // ============ L5: 用户服务 ============
            .route("user-svc", r -> r
                .path("/api/v1/user/**")
                .filters(f -> f
                    .rewritePath("/api/v1/user/(?<segment>.*)", "/api/v1/user/${segment}")
                    .circuitBreaker(c -> c
                        .setName("user-cb")
                        .setFallbackUri("forward:/fallback/generic")))
                .uri("lb://user-svc"))

            // ============ L2: 预留 - 对话管理服务 ============
            .route("conversation-svc", r -> r
                .path("/api/v1/chat/**")
                .filters(f -> f
                    .rewritePath("/api/v1/chat/(?<segment>.*)", "/api/v1/chat/${segment}")
                    .circuitBreaker(c -> c
                        .setName("chat-cb")
                        .setFallbackUri("forward:/fallback/generic")))
                .uri("lb://conversation-svc"))

            .build();
    }
}
