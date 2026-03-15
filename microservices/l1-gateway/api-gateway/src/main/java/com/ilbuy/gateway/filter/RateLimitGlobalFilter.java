package com.ilbuy.gateway.filter;

import com.ilbuy.gateway.config.RateLimitProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.time.Duration;

/**
 * B/C 端差异化限流全局过滤器（滑动窗口令牌计数）
 *
 * <p>规则：
 * <ul>
 *   <li>B端（BUSINESS）：1000次/分钟/IP</li>
 *   <li>C端（CONSUMER）：100次/分钟/用户ID</li>
 *   <li>未鉴权（白名单）：不限流</li>
 * </ul>
 *
 * <p>实现：Redis INCR + EXPIRE 滑动计数窗口。
 *
 * @author ILbuy Team
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class RateLimitGlobalFilter implements GlobalFilter, Ordered {

    private static final int ORDER = -100;   // 在 JWT 过滤器之后执行

    private final RateLimitProperties rateLimitProps;
    private final ReactiveStringRedisTemplate redisTemplate;

    private final AntPathMatcher pathMatcher = new AntPathMatcher();

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getURI().getPath();

        // 白名单不限流
        if (isWhitelisted(path)) {
            return chain.filter(exchange);
        }

        String userType = exchange.getRequest().getHeaders().getFirst("X-User-Type");
        String userId = exchange.getRequest().getHeaders().getFirst("X-User-Id");
        String clientIp = getClientIp(exchange);

        String rateLimitKey;
        int limit;

        if ("BUSINESS".equalsIgnoreCase(userType)) {
            rateLimitKey = rateLimitProps.getKeyPrefix() + "b:" + clientIp;
            limit = rateLimitProps.getBusinessLimitPerMin();
        } else {
            // C端或未认证（此时 userId 可能为空，回退到IP限流）
            String identifier = (userId != null && !userId.isEmpty()) ? userId : clientIp;
            rateLimitKey = rateLimitProps.getKeyPrefix() + "c:" + identifier;
            limit = rateLimitProps.getConsumerLimitPerMin();
        }

        return redisTemplate.opsForValue().increment(rateLimitKey)
            .flatMap(count -> {
                if (count == 1) {
                    // 首次计数，设置过期时间（滑动窗口）
                    return redisTemplate.expire(rateLimitKey,
                            Duration.ofSeconds(rateLimitProps.getWindowSeconds()))
                        .then(chain.filter(exchange));
                }
                if (count > limit) {
                    log.warn("[限流] key={} count={} limit={}", rateLimitKey, count, limit);
                    return tooManyRequests(exchange);
                }
                return chain.filter(exchange);
            });
    }

    private String getClientIp(ServerWebExchange exchange) {
        String xForwardedFor = exchange.getRequest().getHeaders().getFirst("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            return xForwardedFor.split(",")[0].trim();
        }
        String remoteAddr = exchange.getRequest().getRemoteAddress() != null
            ? exchange.getRequest().getRemoteAddress().getAddress().getHostAddress()
            : "unknown";
        return remoteAddr;
    }

    private boolean isWhitelisted(String path) {
        for (String pattern : rateLimitProps.getWhitelistPaths()) {
            if (pathMatcher.match(pattern, path)) {
                return true;
            }
        }
        return false;
    }

    private Mono<Void> tooManyRequests(ServerWebExchange exchange) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(HttpStatus.TOO_MANY_REQUESTS);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        response.getHeaders().set("Retry-After", String.valueOf(rateLimitProps.getWindowSeconds()));
        String body = """
            {"code":429,"message":"请求过于频繁，请稍后重试","timestamp":%d}
            """.formatted(System.currentTimeMillis());
        DataBuffer buffer = response.bufferFactory()
            .wrap(body.getBytes(StandardCharsets.UTF_8));
        return response.writeWith(Mono.just(buffer));
    }

    @Override
    public int getOrder() {
        return ORDER;
    }
}
