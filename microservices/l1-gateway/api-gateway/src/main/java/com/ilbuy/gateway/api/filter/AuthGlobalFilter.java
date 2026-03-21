package com.ilbuy.gateway.api.filter;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ilbuy.gateway.api.properties.AuthWhitelistProperties;
import com.ilbuy.gateway.api.properties.JwtGatewayProperties;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import reactor.core.publisher.Mono;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * JWT 鉴权全局过滤器（Order = -100）
 *
 * <p>处理流程：
 * <ol>
 *   <li>白名单路径直接放行（AntPath 匹配）</li>
 *   <li>提取 Authorization: Bearer Token</li>
 *   <li>本地 JJWT 校验签名 + 过期时间（避免每次调用 auth-service）</li>
 *   <li>Redis 黑名单二次检验（防止注销后 Token 仍有效）</li>
 *   <li>校验通过：解析 userId/username/roles/tenantId 写入下游请求头</li>
 *   <li>校验失败：返回 401 JSON（{@code ResultCode.UNAUTHORIZED}）</li>
 * </ol>
 * </p>
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AuthGlobalFilter implements GlobalFilter, Ordered {

    private static final int ORDER = -100;

    // JWT Claims 常量（与 common-security 保持一致）
    private static final String CLAIM_USER_ID   = "userId";
    private static final String CLAIM_USERNAME  = "username";
    private static final String CLAIM_ROLES     = "roles";
    private static final String CLAIM_TENANT_ID = "tenantId";

    // 向下游透传的请求头
    private static final String HEADER_USER_ID   = "X-User-Id";
    private static final String HEADER_USERNAME  = "X-Username";
    private static final String HEADER_ROLES     = "X-Roles";
    private static final String HEADER_TENANT_ID = "X-Tenant-Id";

    private final JwtGatewayProperties          jwtProperties;
    private final AuthWhitelistProperties        whitelistProperties;
    private final ReactiveStringRedisTemplate    redisTemplate;
    private final ObjectMapper                   objectMapper;

    private SecretKey                            secretKey;
    private final AntPathMatcher                 pathMatcher = new AntPathMatcher();

    @PostConstruct
    public void init() {
        byte[] keyBytes = Decoders.BASE64.decode(jwtProperties.getSecret());
        this.secretKey = Keys.hmacShaKeyFor(keyBytes);
    }

    @Override
    public int getOrder() {
        return ORDER;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getPath().value();

        // 白名单放行
        if (isWhitelisted(path)) {
            return chain.filter(exchange);
        }

        // 提取 Token
        String authHeader = exchange.getRequest().getHeaders()
                .getFirst(jwtProperties.getHeaderName());
        if (authHeader == null || !authHeader.startsWith(jwtProperties.getTokenPrefix())) {
            return unauthorized(exchange, "缺少 Authorization Token");
        }
        String token = authHeader.substring(jwtProperties.getTokenPrefix().length());

        // 本地 JWT 校验
        Claims claims;
        try {
            claims = Jwts.parser()
                    .verifyWith(secretKey)
                    .requireIssuer(jwtProperties.getIssuer())
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();
        } catch (ExpiredJwtException e) {
            log.debug("[Auth] Token 已过期 path={}", path);
            return unauthorized(exchange, "Token 已过期，请重新登录");
        } catch (JwtException e) {
            log.warn("[Auth] Token 无效 path={} err={}", path, e.getMessage());
            return unauthorized(exchange, "Token 无效");
        }

        // Redis 黑名单检验（异步）
        String jti           = claims.getId();
        String blacklistKey  = jwtProperties.getBlacklistKeyPrefix() + jti;

        return redisTemplate.hasKey(blacklistKey)
                .flatMap(inBlacklist -> {
                    if (Boolean.TRUE.equals(inBlacklist)) {
                        log.warn("[Auth] Token 已注销 jti={} path={}", jti, path);
                        return unauthorized(exchange, "Token 已注销，请重新登录");
                    }
                    // 鉴权通过：将用户信息注入下游请求头
                    return chain.filter(buildMutatedExchange(exchange, claims));
                });
    }

    // ────────────── 构建携带用户信息的下游请求 ──────────────

    @SuppressWarnings("unchecked")
    private ServerWebExchange buildMutatedExchange(ServerWebExchange exchange, Claims claims) {
        Object userId    = claims.get(CLAIM_USER_ID);
        Object username  = claims.get(CLAIM_USERNAME);
        Object tenantId  = claims.get(CLAIM_TENANT_ID);
        List<?> roles    = claims.get(CLAIM_ROLES, List.class);

        ServerHttpRequest mutatedRequest = exchange.getRequest().mutate()
                .header(HEADER_USER_ID,   userId   != null ? userId.toString()   : "")
                .header(HEADER_USERNAME,  username != null ? username.toString()  : "")
                .header(HEADER_TENANT_ID, tenantId != null ? tenantId.toString() : "")
                .header(HEADER_ROLES,     roles    != null ? String.join(",", (List<String>) roles) : "")
                // 清除 Authorization（下游服务不再需要，减少数据传输）
                .headers(h -> h.remove("Authorization"))
                .build();

        log.debug("[Auth] 鉴权通过 userId={} path={} expire={}",
                userId, exchange.getRequest().getPath().value(),
                claims.getExpiration() != null
                        ? claims.getExpiration().toInstant().getEpochSecond() - Instant.now().getEpochSecond() + "s"
                        : "N/A");

        return exchange.mutate().request(mutatedRequest).build();
    }

    // ────────────── 统一 401 响应 ──────────────

    private Mono<Void> unauthorized(ServerWebExchange exchange, String message) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(HttpStatus.UNAUTHORIZED);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);

        Map<String, Object> body = Map.of(
                "code",      401,
                "message",   message,
                "timestamp", System.currentTimeMillis(),
                "traceId",   exchange.getResponse().getHeaders()
                                     .getFirst(TraceIdGlobalFilter.TRACE_ID_HEADER)
        );

        byte[] bytes;
        try {
            bytes = objectMapper.writeValueAsBytes(body);
        } catch (JsonProcessingException e) {
            bytes = ("{\"code\":401,\"message\":\"" + message + "\"}").getBytes(StandardCharsets.UTF_8);
        }

        DataBuffer buffer = response.bufferFactory().wrap(bytes);
        return response.writeWith(Mono.just(buffer));
    }

    // ────────────── 白名单匹配 ──────────────

    private boolean isWhitelisted(String path) {
        return whitelistProperties.getWhitelist().stream()
                .anyMatch(pattern -> pathMatcher.match(pattern, path));
    }
}
