package com.health.physical.gateway.filter;

import com.alibaba.fastjson2.JSON;
import com.health.physical.common.constant.PermissionConstants;
import com.health.physical.common.dto.Result;
import com.health.physical.common.util.JwtUtil;
import com.health.physical.gateway.config.GatewayProperties;
import io.jsonwebtoken.Claims;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RBucket;
import org.redisson.api.RedissonClient;
import org.springframework.cloud.gateway.filter.GatewayFilter;
import org.springframework.cloud.gateway.filter.factory.AbstractGatewayFilterFactory;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;

/**
 * JWT鉴权网关过滤器
 * <p>
 * 修复：原 @Value("#{'${gateway.white-list}'.split(',')}") 在 YAML list 格式下
 * 会抛 ConversionFailedException，改为注入 GatewayProperties（@ConfigurationProperties）。
 */
@Slf4j
@Component
public class AuthFilter extends AbstractGatewayFilterFactory<AuthFilter.Config> {

    private static final AntPathMatcher PATH_MATCHER = new AntPathMatcher();

    private final GatewayProperties gatewayProperties;
    private final RedissonClient redissonClient;

    public AuthFilter(GatewayProperties gatewayProperties, RedissonClient redissonClient) {
        super(Config.class);
        this.gatewayProperties = gatewayProperties;
        this.redissonClient = redissonClient;
    }

    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            ServerHttpRequest request = exchange.getRequest();
            String path = request.getURI().getPath();

            // 白名单直接放行
            if (isWhiteListed(path)) {
                return chain.filter(exchange);
            }

            // 获取 Authorization 头
            String authorization = request.getHeaders().getFirst(PermissionConstants.TOKEN_HEADER);
            if (authorization == null || !authorization.startsWith(PermissionConstants.TOKEN_PREFIX)) {
                return writeUnauthorized(exchange.getResponse(), "未携带Token，请先登录");
            }

            String token = authorization.substring(PermissionConstants.TOKEN_PREFIX.length());

            // 验证 JWT 签名及有效期
            Claims claims = JwtUtil.parseToken(token, gatewayProperties.getJwtSecret());
            if (claims == null) {
                return writeUnauthorized(exchange.getResponse(), "Token无效或已过期，请重新登录");
            }

            // 验证 Redis 中 Token 是否仍存活（防止 logout 后重用）
            String tokenKey = PermissionConstants.REDIS_TOKEN_PREFIX + token;
            RBucket<String> tokenBucket = redissonClient.getBucket(tokenKey);
            if (!tokenBucket.isExists()) {
                return writeUnauthorized(exchange.getResponse(), "Token已失效，请重新登录");
            }

            // 将医生标识注入下游请求头
            String docId   = (String) claims.get("docId");
            String docName = (String) claims.get("name");
            ServerHttpRequest mutatedRequest = request.mutate()
                    .header("X-Doc-Id",   docId   != null ? docId   : "")
                    .header("X-Doc-Name", docName != null ? docName : "")
                    .build();

            log.debug("鉴权通过: path={}, docId={}", path, docId);
            return chain.filter(exchange.mutate().request(mutatedRequest).build());
        };
    }

    private boolean isWhiteListed(String path) {
        for (String pattern : gatewayProperties.getWhiteList()) {
            if (PATH_MATCHER.match(pattern.trim(), path)) {
                return true;
            }
        }
        return false;
    }

    private Mono<Void> writeUnauthorized(ServerHttpResponse response, String message) {
        response.setStatusCode(HttpStatus.UNAUTHORIZED);
        response.getHeaders().add(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE);
        Result<Void> result = Result.unauthorized(message);
        byte[] bytes = JSON.toJSONString(result).getBytes(StandardCharsets.UTF_8);
        DataBuffer buffer = response.bufferFactory().wrap(bytes);
        return response.writeWith(Mono.just(buffer));
    }

    public static class Config {
    }
}
