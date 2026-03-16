package com.ilbuy.gateway.config;

import com.ilbuy.gateway.filter.JwtAuthGlobalFilter;
import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver;
import org.springframework.cloud.gateway.filter.ratelimit.RedisRateLimiter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import reactor.core.publisher.Mono;

/**
 * Redis 令牌桶限流配置
 *
 * 限流维度优先级：
 *   1. 已登录用户 → 按 X-User-Id（精确限流）
 *   2. 未登录请求 → 按 IP（防暴力）
 */
@Configuration
public class RateLimiterConfig {

    /**
     * 已登录用户：按 userId 限流
     * 白名单路径（登录/注册）未注入 X-User-Id，走 ipKeyResolver
     */
    @Bean
    @Primary
    public KeyResolver userKeyResolver() {
        return exchange -> {
            String userId = exchange.getRequest()
                    .getHeaders()
                    .getFirst(JwtAuthGlobalFilter.HEADER_USER_ID);
            if (userId != null && !userId.isBlank()) {
                return Mono.just("user:" + userId);
            }
            // 降级：按 IP
            String ip = exchange.getRequest().getRemoteAddress() != null
                    ? exchange.getRequest().getRemoteAddress().getAddress().getHostAddress()
                    : "unknown";
            return Mono.just("ip:" + ip);
        };
    }

    /**
     * 默认限流器：
     *   replenishRate  = 20 req/s（令牌生成速率）
     *   burstCapacity  = 40（桶容量，允许短暂突刺）
     *   requestedTokens = 1（每次消耗令牌数）
     *
     * 各路由可在 application.yml 的 args 中覆盖
     */
    @Bean
    public RedisRateLimiter defaultRedisRateLimiter() {
        return new RedisRateLimiter(20, 40, 1);
    }
}
