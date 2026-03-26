package com.hd.gateway.filter;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.hd.common.util.JwtUtils;
import com.hd.gateway.config.HdGatewayProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Component
public class JwtAuthFilter implements GlobalFilter, Ordered {

    private static final Logger log = LoggerFactory.getLogger(JwtAuthFilter.class);

    private static final String BEARER_PREFIX = "Bearer ";
    private static final String BLACKLIST_KEY_PREFIX = "token:logout:";

    private final JwtUtils jwtUtils;
    private final HdGatewayProperties gatewayProperties;
    private final ReactiveStringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;
    private final AntPathMatcher pathMatcher = new AntPathMatcher();

    public JwtAuthFilter(JwtUtils jwtUtils,
                         HdGatewayProperties gatewayProperties,
                         ReactiveStringRedisTemplate redisTemplate,
                         ObjectMapper objectMapper) {
        this.jwtUtils = jwtUtils;
        this.gatewayProperties = gatewayProperties;
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
    }

    @Override
    public int getOrder() {
        return -100;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getURI().getPath();

        // Handle CORS preflight
        if (request.getMethod() == HttpMethod.OPTIONS) {
            return chain.filter(exchange);
        }

        // Check white list
        if (isWhiteListed(path)) {
            log.debug("Path {} is white-listed, skipping JWT auth", path);
            return chain.filter(exchange);
        }

        // Extract Authorization header
        String authHeader = request.getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        if (authHeader == null || !authHeader.startsWith(BEARER_PREFIX)) {
            log.warn("Missing or invalid Authorization header for path: {}", path);
            return writeUnauthorizedResponse(exchange, "未登录或Token已过期");
        }

        String token = authHeader.substring(BEARER_PREFIX.length()).trim();

        // Validate token signature and expiry
        if (!jwtUtils.validateToken(token)) {
            log.warn("Invalid or expired JWT token for path: {}", path);
            return writeUnauthorizedResponse(exchange, "未登录或Token已过期");
        }

        // Check Redis blacklist (token was explicitly logged out)
        String blacklistKey = BLACKLIST_KEY_PREFIX + token;
        return redisTemplate.hasKey(blacklistKey)
                .flatMap(isBlacklisted -> {
                    if (Boolean.TRUE.equals(isBlacklisted)) {
                        log.warn("Token is blacklisted (logged out) for path: {}", path);
                        return writeUnauthorizedResponse(exchange, "未登录或Token已过期");
                    }

                    // Extract user info and forward downstream headers
                    Long userId = jwtUtils.extractUserId(token);
                    String username = jwtUtils.extractUsername(token);
                    List<String> permissions = jwtUtils.extractPermissions(token);
                    String permissionsStr = permissions != null ? String.join(",", permissions) : "";

                    log.debug("Authenticated user: userId={}, username={}, path={}", userId, username, path);

                    ServerHttpRequest mutatedRequest = request.mutate()
                            .header("X-User-Id", String.valueOf(userId))
                            .header("X-Username", username != null ? username : "")
                            .header("X-Permissions", permissionsStr)
                            .build();

                    return chain.filter(exchange.mutate().request(mutatedRequest).build());
                })
                .onErrorResume(e -> {
                    log.error("Error during JWT filter processing for path: {}", path, e);
                    return writeUnauthorizedResponse(exchange, "认证服务异常");
                });
    }

    private boolean isWhiteListed(String path) {
        List<String> whiteList = gatewayProperties.getWhiteList();
        if (whiteList == null || whiteList.isEmpty()) {
            return false;
        }
        for (String pattern : whiteList) {
            if (pathMatcher.match(pattern, path)) {
                return true;
            }
        }
        return false;
    }

    private Mono<Void> writeUnauthorizedResponse(ServerWebExchange exchange, String message) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(HttpStatus.UNAUTHORIZED);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);

        Map<String, Object> body = new HashMap<>();
        body.put("code", 401);
        body.put("message", message);
        body.put("data", null);

        byte[] bytes;
        try {
            bytes = objectMapper.writeValueAsBytes(body);
        } catch (JsonProcessingException e) {
            bytes = "{\"code\":401,\"message\":\"未登录或Token已过期\"}".getBytes(StandardCharsets.UTF_8);
        }

        DataBuffer buffer = response.bufferFactory().wrap(bytes);
        return response.writeWith(Mono.just(buffer));
    }
}
