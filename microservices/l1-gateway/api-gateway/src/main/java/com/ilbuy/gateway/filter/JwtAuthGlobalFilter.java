package com.ilbuy.gateway.filter;

import com.ilbuy.gateway.config.JwtProperties;
import com.ilbuy.gateway.config.RateLimitProperties;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;

/**
 * JWT 全局鉴权过滤器（最高优先级）
 *
 * <p>处理流程：
 * <ol>
 *   <li>白名单路径直接放行</li>
 *   <li>提取 Bearer Token，缺失返回 401</li>
 *   <li>验证 JWT 签名与有效期</li>
 *   <li>查询 Redis 黑名单（logout 后的 token）</li>
 *   <li>解析 userId / userType / roles，注入下游请求头</li>
 * </ol>
 *
 * @author ILbuy Team
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class JwtAuthGlobalFilter implements GlobalFilter, Ordered {

    private static final int ORDER = -200;
    private static final String BEARER_PREFIX = "Bearer ";
    private static final String HEADER_USER_ID = "X-User-Id";
    private static final String HEADER_USER_TYPE = "X-User-Type";
    private static final String HEADER_USER_ROLES = "X-User-Roles";

    private final JwtProperties jwtProperties;
    private final RateLimitProperties rateLimitProperties;
    private final ReactiveStringRedisTemplate redisTemplate;

    private final AntPathMatcher pathMatcher = new AntPathMatcher();

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getURI().getPath();

        // 白名单放行
        if (isWhitelisted(path)) {
            return chain.filter(exchange);
        }

        String authHeader = exchange.getRequest().getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        if (authHeader == null || !authHeader.startsWith(BEARER_PREFIX)) {
            return unauthorized(exchange, "缺少认证令牌");
        }

        String token = authHeader.substring(BEARER_PREFIX.length());

        Claims claims;
        try {
            claims = parseToken(token);
        } catch (ExpiredJwtException e) {
            return unauthorized(exchange, "令牌已过期，请重新登录");
        } catch (JwtException e) {
            return unauthorized(exchange, "令牌无效");
        }

        String jti = claims.getId();
        String blacklistKey = jwtProperties.getBlacklistKeyPrefix() + jti;

        // 异步查 Redis 黑名单
        return redisTemplate.hasKey(blacklistKey)
            .flatMap(isBlacklisted -> {
                if (Boolean.TRUE.equals(isBlacklisted)) {
                    return unauthorized(exchange, "令牌已注销，请重新登录");
                }
                // 将用户信息透传到下游服务
                String userId = claims.getSubject();
                String userType = claims.get("userType", String.class);
                String roles = claims.get("roles", String.class);

                ServerHttpRequest mutatedRequest = exchange.getRequest().mutate()
                    .header(HEADER_USER_ID, userId)
                    .header(HEADER_USER_TYPE, userType != null ? userType : "")
                    .header(HEADER_USER_ROLES, roles != null ? roles : "")
                    // 防止外部伪造内部头
                    .headers(h -> h.remove("X-Internal-Token"))
                    .build();

                return chain.filter(exchange.mutate().request(mutatedRequest).build());
            });
    }

    private Claims parseToken(String token) {
        SecretKey key = Keys.hmacShaKeyFor(jwtProperties.getSecret().getBytes(StandardCharsets.UTF_8));
        return Jwts.parser()
            .verifyWith(key)
            .build()
            .parseSignedClaims(token)
            .getPayload();
    }

    private boolean isWhitelisted(String path) {
        for (String pattern : rateLimitProperties.getWhitelistPaths()) {
            if (pathMatcher.match(pattern, path)) {
                return true;
            }
        }
        return false;
    }

    private Mono<Void> unauthorized(ServerWebExchange exchange, String message) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(HttpStatus.UNAUTHORIZED);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        String body = """
            {"code":401,"message":"%s","timestamp":%d}
            """.formatted(message, System.currentTimeMillis());
        DataBuffer buffer = response.bufferFactory()
            .wrap(body.getBytes(StandardCharsets.UTF_8));
        return response.writeWith(Mono.just(buffer));
    }

    @Override
    public int getOrder() {
        return ORDER;
    }
}
