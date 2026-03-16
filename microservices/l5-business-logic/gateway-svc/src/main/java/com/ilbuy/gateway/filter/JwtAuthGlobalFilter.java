package com.ilbuy.gateway.filter;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ilbuy.gateway.security.JwtUtil;
import io.jsonwebtoken.Claims;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.util.StringUtils;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * 全局 JWT 鉴权过滤器（优先级最高）
 *
 * 白名单路径直接放行；其余路径必须携带合法 Bearer Token。
 * 验证通过后将 X-User-Id / X-User-Role / X-Username 注入下游请求头，
 * 同时删除客户端传入的同名头，防止伪造。
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class JwtAuthGlobalFilter implements GlobalFilter, Ordered {

    private static final int ORDER = -200;          // 早于 RouteToRequestUrlFilter(-10000 以外)
    private static final String BEARER_PREFIX = "Bearer ";
    private static final AntPathMatcher PATH_MATCHER = new AntPathMatcher();

    /** 下游服务约定的身份头 */
    public static final String HEADER_USER_ID   = "X-User-Id";
    public static final String HEADER_USER_ROLE = "X-User-Role";
    public static final String HEADER_USERNAME  = "X-Username";

    private final JwtUtil      jwtUtil;
    private final ObjectMapper objectMapper;

    /** 白名单：无需 JWT 的路径（支持 Ant 通配符） */
    @Value("${gateway.whitelist:/api/v1/auth/**,/actuator/**}")
    private List<String> whitelist;

    @Override
    public int getOrder() {
        return ORDER;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getPath().value();

        // 1. 白名单放行
        if (isWhitelisted(path)) {
            return chain.filter(exchange);
        }

        // 2. 提取 Token
        String token = resolveToken(request);
        if (!StringUtils.hasText(token)) {
            return reject(exchange, HttpStatus.UNAUTHORIZED, "缺少认证令牌");
        }

        // 3. 验证 Token
        if (!jwtUtil.validate(token)) {
            return reject(exchange, HttpStatus.UNAUTHORIZED, "令牌无效或已过期");
        }

        // 4. 解析 Claims，注入下游头
        Claims claims = jwtUtil.parse(token);
        String userId   = claims.getSubject();
        String role     = claims.get("role",     String.class);
        String username = claims.get("username", String.class);

        log.debug("JWT OK: userId={} role={} path={}", userId, role, path);

        ServerHttpRequest mutated = request.mutate()
                // 清除客户端伪造头
                .headers(h -> {
                    h.remove(HEADER_USER_ID);
                    h.remove(HEADER_USER_ROLE);
                    h.remove(HEADER_USERNAME);
                })
                .header(HEADER_USER_ID,   userId)
                .header(HEADER_USER_ROLE, role)
                .header(HEADER_USERNAME,  username)
                .build();

        return chain.filter(exchange.mutate().request(mutated).build());
    }

    // ── 私有工具 ────────────────────────────────────────────────

    private boolean isWhitelisted(String path) {
        return whitelist.stream().anyMatch(pattern -> PATH_MATCHER.match(pattern, path));
    }

    private String resolveToken(ServerHttpRequest request) {
        String bearer = request.getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        if (StringUtils.hasText(bearer) && bearer.startsWith(BEARER_PREFIX)) {
            return bearer.substring(BEARER_PREFIX.length());
        }
        return null;
    }

    private Mono<Void> reject(ServerWebExchange exchange, HttpStatus status, String message) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(status);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);

        Map<String, Object> body = Map.of(
                "timestamp", Instant.now().toString(),
                "status",    status.value(),
                "error",     status.getReasonPhrase(),
                "message",   message,
                "path",      exchange.getRequest().getPath().value()
        );

        byte[] bytes;
        try {
            bytes = objectMapper.writeValueAsBytes(body);
        } catch (JsonProcessingException e) {
            bytes = ("{\"message\":\"" + message + "\"}").getBytes(StandardCharsets.UTF_8);
        }

        DataBuffer buffer = response.bufferFactory().wrap(bytes);
        return response.writeWith(Mono.just(buffer));
    }
}
