package com.health.physical.gateway.filter;

import com.alibaba.fastjson2.JSON;
import com.health.physical.common.constant.PermissionConstants;
import com.health.physical.common.dto.Result;
import com.health.physical.common.util.JwtUtil;
import io.jsonwebtoken.Claims;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RBucket;
import org.redisson.api.RedissonClient;
import org.springframework.beans.factory.annotation.Value;
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
import java.util.Arrays;
import java.util.List;

/**
 * JWT鉴权网关过滤器
 */
@Slf4j
@Component
public class AuthFilter extends AbstractGatewayFilterFactory<AuthFilter.Config> {

    private static final AntPathMatcher PATH_MATCHER = new AntPathMatcher();

    @Value("${jwt.secret:physical_health_system_jwt_secret_key_2024_secure_enough}")
    private String jwtSecret;

    @Value("#{'${gateway.white-list:/api/auth/login}'.split(',')}")
    private List<String> whiteList;

    private final RedissonClient redissonClient;

    public AuthFilter(RedissonClient redissonClient) {
        super(Config.class);
        this.redissonClient = redissonClient;
    }

    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            ServerHttpRequest request = exchange.getRequest();
            String path = request.getURI().getPath();

            // 白名单跳过鉴权
            if (isWhiteListed(path)) {
                return chain.filter(exchange);
            }

            // 获取Token
            String authorization = request.getHeaders().getFirst(PermissionConstants.TOKEN_HEADER);
            if (authorization == null || !authorization.startsWith(PermissionConstants.TOKEN_PREFIX)) {
                return writeUnauthorized(exchange.getResponse(), "未携带Token，请先登录");
            }

            String token = authorization.substring(PermissionConstants.TOKEN_PREFIX.length());

            // 验证JWT
            Claims claims = JwtUtil.parseToken(token, jwtSecret);
            if (claims == null) {
                return writeUnauthorized(exchange.getResponse(), "Token无效或已过期，请重新登录");
            }

            // 检查Redis中Token是否有效（防logout后重用）
            String tokenKey = PermissionConstants.REDIS_TOKEN_PREFIX + token;
            RBucket<String> tokenBucket = redissonClient.getBucket(tokenKey);
            if (!tokenBucket.isExists()) {
                return writeUnauthorized(exchange.getResponse(), "Token已失效，请重新登录");
            }

            // 将医生信息注入请求头，供下游服务使用
            String docId = (String) claims.get("docId");
            String docName = (String) claims.get("name");
            ServerHttpRequest mutatedRequest = request.mutate()
                    .header("X-Doc-Id", docId != null ? docId : "")
                    .header("X-Doc-Name", docName != null ? docName : "")
                    .build();

            log.debug("鉴权通过: path={}, docId={}", path, docId);
            return chain.filter(exchange.mutate().request(mutatedRequest).build());
        };
    }

    private boolean isWhiteListed(String path) {
        for (String pattern : whiteList) {
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
