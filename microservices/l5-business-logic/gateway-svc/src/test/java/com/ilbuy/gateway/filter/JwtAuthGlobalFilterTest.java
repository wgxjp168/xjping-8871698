package com.ilbuy.gateway.filter;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ilbuy.gateway.security.JwtUtil;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class JwtAuthGlobalFilterTest {

    private static final String SECRET = "ilbuy-user-svc-secret-key-must-be-at-least-32-chars";
    private static final SecretKey KEY =
            Keys.hmacShaKeyFor(SECRET.getBytes(StandardCharsets.UTF_8));

    @Mock GatewayFilterChain chain;

    private JwtUtil              jwtUtil;
    private JwtAuthGlobalFilter  filter;

    @BeforeEach
    void setUp() {
        jwtUtil = new JwtUtil(SECRET);
        filter  = new JwtAuthGlobalFilter(jwtUtil, new ObjectMapper());
        // 设置白名单
        var f = filter;
        try {
            var field = JwtAuthGlobalFilter.class.getDeclaredField("whitelist");
            field.setAccessible(true);
            field.set(f, List.of("/api/v1/auth/**", "/actuator/**"));
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    private String buildToken(Long userId, String role) {
        return Jwts.builder()
                .subject(String.valueOf(userId))
                .claim("role", role)
                .claim("username", "testUser")
                .issuedAt(new Date())
                .expiration(new Date(System.currentTimeMillis() + 86_400_000L))
                .signWith(KEY)
                .compact();
    }

    @Test
    void whitelistedPath_passesWithoutToken() {
        MockServerHttpRequest request = MockServerHttpRequest
                .get("/api/v1/auth/login").build();
        MockServerWebExchange exchange = MockServerWebExchange.from(request);

        when(chain.filter(any())).thenReturn(Mono.empty());

        StepVerifier.create(filter.filter(exchange, chain))
                .verifyComplete();

        verify(chain).filter(any());
    }

    @Test
    void missingToken_returns401() {
        MockServerHttpRequest request = MockServerHttpRequest
                .get("/api/v1/orders").build();
        MockServerWebExchange exchange = MockServerWebExchange.from(request);

        StepVerifier.create(filter.filter(exchange, chain))
                .verifyComplete();

        assertThat(exchange.getResponse().getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED);
        verify(chain, never()).filter(any());
    }

    @Test
    void validToken_injectsHeadersAndPasses() {
        String token = buildToken(7L, "B2C");
        MockServerHttpRequest request = MockServerHttpRequest
                .get("/api/v1/orders")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                .build();
        MockServerWebExchange exchange = MockServerWebExchange.from(request);

        when(chain.filter(any())).thenAnswer(inv -> {
            MockServerWebExchange ex = inv.getArgument(0);
            // 验证注入的请求头
            assertThat(ex.getRequest().getHeaders().getFirst("X-User-Id")).isEqualTo("7");
            assertThat(ex.getRequest().getHeaders().getFirst("X-User-Role")).isEqualTo("B2C");
            return Mono.empty();
        });

        StepVerifier.create(filter.filter(exchange, chain))
                .verifyComplete();

        verify(chain).filter(any());
    }

    @Test
    void invalidToken_returns401() {
        MockServerHttpRequest request = MockServerHttpRequest
                .get("/api/v1/orders")
                .header(HttpHeaders.AUTHORIZATION, "Bearer invalid.token.here")
                .build();
        MockServerWebExchange exchange = MockServerWebExchange.from(request);

        StepVerifier.create(filter.filter(exchange, chain))
                .verifyComplete();

        assertThat(exchange.getResponse().getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED);
    }

    @Test
    void spoofedUserIdHeader_isStrippedAndReplacedByJwt() {
        String token = buildToken(42L, "B2C");
        MockServerHttpRequest request = MockServerHttpRequest
                .get("/api/v1/users/me")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                .header("X-User-Id", "999")   // 客户端伪造
                .build();
        MockServerWebExchange exchange = MockServerWebExchange.from(request);

        when(chain.filter(any())).thenAnswer(inv -> {
            MockServerWebExchange ex = inv.getArgument(0);
            // 伪造头已被 JWT 中的真实值覆盖
            assertThat(ex.getRequest().getHeaders().getFirst("X-User-Id")).isEqualTo("42");
            return Mono.empty();
        });

        StepVerifier.create(filter.filter(exchange, chain))
                .verifyComplete();
    }
}
