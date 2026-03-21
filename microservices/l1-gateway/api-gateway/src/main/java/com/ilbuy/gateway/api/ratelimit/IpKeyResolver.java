package com.ilbuy.gateway.api.ratelimit;

import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.Optional;

/**
 * B端 API 限流 Key 解析器（1000 请求/分钟/IP）
 *
 * <p>Key = 客户端真实 IP（支持反向代理透传的 X-Forwarded-For）</p>
 *
 * <p>应用于 B端 API 路由：{@code /api/v1/open/**}、{@code /api/v1/b/**}</p>
 */
public class IpKeyResolver implements KeyResolver {

    private static final String RATE_LIMIT_PREFIX = "rl:ip:";

    @Override
    public Mono<String> resolve(ServerWebExchange exchange) {
        return Mono.just(RATE_LIMIT_PREFIX + resolveIp(exchange));
    }

    private String resolveIp(ServerWebExchange exchange) {
        // 1. X-Real-IP（Nginx 直接代理）
        String realIp = exchange.getRequest().getHeaders().getFirst("X-Real-IP");
        if (realIp != null && !realIp.isBlank()) {
            return realIp.trim();
        }

        // 2. X-Forwarded-For（取第一个非私网 IP）
        String xff = exchange.getRequest().getHeaders().getFirst("X-Forwarded-For");
        if (xff != null && !xff.isBlank()) {
            return xff.split(",")[0].trim();
        }

        // 3. 直连 IP（本地/测试环境）
        return Optional.ofNullable(exchange.getRequest().getRemoteAddress())
                .map(addr -> addr.getAddress().getHostAddress())
                .orElse("unknown");
    }
}
