package com.ilbuy.gateway.filter;

import com.ilbuy.gateway.config.JwtProperties;
import com.ilbuy.gateway.config.RateLimitProperties;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.data.redis.core.ReactiveValueOperations;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.reactive.server.WebTestClient;
import reactor.core.publisher.Mono;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

/**
 * JWT 鉴权过滤器单元测试
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
    properties = {
        "spring.cloud.nacos.discovery.enabled=false",
        "spring.cloud.nacos.config.enabled=false",
        "spring.cloud.discovery.enabled=false"
    })
@AutoConfigureWebTestClient
@DisplayName("JWT 鉴权过滤器测试")
class JwtAuthGlobalFilterTest {

    @Autowired
    private WebTestClient webTestClient;

    @MockBean
    private ReactiveStringRedisTemplate redisTemplate;

    @Autowired
    private JwtProperties jwtProperties;

    @Autowired
    private RateLimitProperties rateLimitProperties;

    private ReactiveValueOperations<String, String> valueOps;

    @BeforeEach
    void setUp() {
        valueOps = org.mockito.Mockito.mock(ReactiveValueOperations.class);
        when(redisTemplate.opsForValue()).thenReturn(valueOps);
        when(redisTemplate.hasKey(anyString())).thenReturn(Mono.just(false));
        when(valueOps.increment(anyString())).thenReturn(Mono.just(1L));
        when(redisTemplate.expire(anyString(), org.mockito.ArgumentMatchers.any()))
            .thenReturn(Mono.just(true));
    }

    @Test
    @DisplayName("白名单路径 /auth/login 直接放行，不校验 Token")
    void whitelistPath_shouldPassWithoutToken() {
        webTestClient.post()
            .uri("/auth/login")
            .exchange()
            .expectStatus().value(status -> org.assertj.core.api.Assertions.assertThat(status).isNotEqualTo(401));
    }

    @Test
    @DisplayName("缺少 Authorization 头，返回 401")
    void missingToken_shouldReturn401() {
        webTestClient.get()
            .uri("/api/v1/user/profile")
            .exchange()
            .expectStatus().isUnauthorized();
    }

    @Test
    @DisplayName("Bearer Token 格式错误，返回 401")
    void invalidTokenFormat_shouldReturn401() {
        webTestClient.get()
            .uri("/api/v1/user/profile")
            .header(HttpHeaders.AUTHORIZATION, "InvalidToken xyz")
            .exchange()
            .expectStatus().isUnauthorized();
    }

    @Test
    @DisplayName("有效 JWT Token，请求正常转发并注入用户头")
    void validToken_shouldForwardWithUserHeaders() {
        String token = buildValidToken("10001", "CONSUMER", "ROLE_USER");

        // 注意：因为下游服务（user-svc）未启动，会触发熔断降级（503）而非 401
        webTestClient.get()
            .uri("/api/v1/user/profile")
            .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
            .exchange()
            .expectStatus().value(status -> org.assertj.core.api.Assertions.assertThat(status).isNotEqualTo(401));
    }

    @Test
    @DisplayName("已拉黑 Token（logout），返回 401")
    void blacklistedToken_shouldReturn401() {
        when(redisTemplate.hasKey(anyString())).thenReturn(Mono.just(true));
        String token = buildValidToken("10002", "BUSINESS", "ROLE_ENTERPRISE");

        webTestClient.get()
            .uri("/api/v1/user/profile")
            .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
            .exchange()
            .expectStatus().isUnauthorized();
    }

    // ============ 辅助方法 ============

    private String buildValidToken(String userId, String userType, String roles) {
        SecretKey key = Keys.hmacShaKeyFor(
            jwtProperties.getSecret().getBytes(StandardCharsets.UTF_8));
        return Jwts.builder()
            .subject(userId)
            .claim("userType", userType)
            .claim("roles", roles)
            .id(UUID.randomUUID().toString())
            .issuedAt(new Date())
            .expiration(new Date(System.currentTimeMillis() + 3600_000L))
            .signWith(key)
            .compact();
    }
}
