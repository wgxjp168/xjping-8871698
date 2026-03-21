package com.ilbuy.gateway.api.ratelimit;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import javax.crypto.SecretKey;
import java.util.Optional;

/**
 * C端用户限流 Key 解析器（100 请求/分钟/用户）
 *
 * <p>Key 提取策略（优先级从高到低）：
 * <ol>
 *   <li>从 JWT 解析 userId — 已登录用户精确限流</li>
 *   <li>从 X-User-Id 请求头取（网关已转发场景）</li>
 *   <li>回退为客户端 IP — 匿名用户兜底</li>
 * </ol>
 * </p>
 */
@Slf4j
public class UserKeyResolver implements KeyResolver {

    private static final String CLAIM_USER_ID = "userId";
    private static final String HEADER_USER_ID = "X-User-Id";
    private static final String HEADER_AUTHORIZATION = "Authorization";
    private static final String TOKEN_PREFIX = "Bearer ";
    private static final String RATE_LIMIT_PREFIX = "rl:user:";

    private final SecretKey secretKey;

    public UserKeyResolver(String jwtSecret) {
        byte[] keyBytes = Decoders.BASE64.decode(jwtSecret);
        this.secretKey = Keys.hmacShaKeyFor(keyBytes);
    }

    @Override
    public Mono<String> resolve(ServerWebExchange exchange) {
        return Mono.just(resolveKey(exchange));
    }

    private String resolveKey(ServerWebExchange exchange) {
        // 1. JWT → userId
        String authHeader = exchange.getRequest().getHeaders().getFirst(HEADER_AUTHORIZATION);
        if (authHeader != null && authHeader.startsWith(TOKEN_PREFIX)) {
            String token = authHeader.substring(TOKEN_PREFIX.length());
            try {
                Claims claims = Jwts.parser()
                        .verifyWith(secretKey)
                        .build()
                        .parseSignedClaims(token)
                        .getPayload();
                Object userId = claims.get(CLAIM_USER_ID);
                if (userId != null) {
                    return RATE_LIMIT_PREFIX + userId;
                }
            } catch (Exception e) {
                log.debug("[RateLimit] JWT 解析失败，回退到 X-User-Id: {}", e.getMessage());
            }
        }

        // 2. X-User-Id 请求头
        String userId = exchange.getRequest().getHeaders().getFirst(HEADER_USER_ID);
        if (userId != null && !userId.isBlank()) {
            return RATE_LIMIT_PREFIX + userId;
        }

        // 3. 客户端 IP 兜底
        return RATE_LIMIT_PREFIX + getClientIp(exchange);
    }

    private String getClientIp(ServerWebExchange exchange) {
        // 优先取反向代理透传的真实 IP
        return Optional.ofNullable(exchange.getRequest().getHeaders().getFirst("X-Forwarded-For"))
                .map(xff -> xff.split(",")[0].trim())
                .orElseGet(() -> Optional.ofNullable(exchange.getRequest().getRemoteAddress())
                        .map(addr -> addr.getAddress().getHostAddress())
                        .orElse("unknown"));
    }
}
