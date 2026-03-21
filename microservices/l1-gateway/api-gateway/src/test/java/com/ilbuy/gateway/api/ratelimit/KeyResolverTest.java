package com.ilbuy.gateway.api.ratelimit;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import reactor.test.StepVerifier;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 限流 Key 解析器单元测试
 */
@DisplayName("限流 Key 解析器单元测试")
class KeyResolverTest {

    // ─────── IpKeyResolver ───────

    @Nested
    @DisplayName("IpKeyResolver")
    class IpKeyResolverTests {

        private IpKeyResolver resolver;

        @BeforeEach
        void setUp() {
            resolver = new IpKeyResolver();
        }

        @Test
        @DisplayName("有 X-Real-IP 时使用真实 IP")
        void realIpHeader_usesRealIp() {
            MockServerHttpRequest request = MockServerHttpRequest.get("/api/test")
                    .header("X-Real-IP", "1.2.3.4")
                    .build();

            StepVerifier.create(resolver.resolve(MockServerWebExchange.from(request)))
                    .assertNext(key -> assertThat(key).isEqualTo("rl:ip:1.2.3.4"))
                    .verifyComplete();
        }

        @Test
        @DisplayName("有 X-Forwarded-For 时取第一个 IP")
        void xForwardedFor_takesFirst() {
            MockServerHttpRequest request = MockServerHttpRequest.get("/api/test")
                    .header("X-Forwarded-For", "5.6.7.8, 192.168.1.1")
                    .build();

            StepVerifier.create(resolver.resolve(MockServerWebExchange.from(request)))
                    .assertNext(key -> assertThat(key).isEqualTo("rl:ip:5.6.7.8"))
                    .verifyComplete();
        }

        @Test
        @DisplayName("Key 前缀为 rl:ip:")
        void keyPrefix_isRlIp() {
            MockServerHttpRequest request = MockServerHttpRequest.get("/api/test")
                    .header("X-Real-IP", "9.9.9.9")
                    .build();

            StepVerifier.create(resolver.resolve(MockServerWebExchange.from(request)))
                    .assertNext(key -> assertThat(key).startsWith("rl:ip:"))
                    .verifyComplete();
        }

        @Test
        @DisplayName("X-Real-IP 优先于 X-Forwarded-For")
        void realIpPriorityOverXff() {
            MockServerHttpRequest request = MockServerHttpRequest.get("/api/test")
                    .header("X-Real-IP", "1.1.1.1")
                    .header("X-Forwarded-For", "2.2.2.2")
                    .build();

            StepVerifier.create(resolver.resolve(MockServerWebExchange.from(request)))
                    .assertNext(key -> assertThat(key).isEqualTo("rl:ip:1.1.1.1"))
                    .verifyComplete();
        }
    }

    // ─────── UserKeyResolver（无 JWT 场景，回退到 IP） ───────

    @Nested
    @DisplayName("UserKeyResolver — 无 JWT 场景")
    class UserKeyResolverFallbackTests {

        private UserKeyResolver resolver;

        @BeforeEach
        void setUp() {
            // 使用合法的 256bit Base64 密钥（测试专用）
            resolver = new UserKeyResolver("aWxidXktcGxhdGZvcm0tc2VjcmV0LWtleS0zMmJ5dGVz");
        }

        @Test
        @DisplayName("无 Authorization 头 → 回退到 X-User-Id")
        void noJwt_fallbackToUserId() {
            MockServerHttpRequest request = MockServerHttpRequest.get("/api/test")
                    .header("X-User-Id", "42")
                    .build();

            StepVerifier.create(resolver.resolve(MockServerWebExchange.from(request)))
                    .assertNext(key -> assertThat(key).isEqualTo("rl:user:42"))
                    .verifyComplete();
        }

        @Test
        @DisplayName("无任何用户标识 → 回退到 clientIP")
        void noJwtNoUserId_fallbackToIp() {
            MockServerHttpRequest request = MockServerHttpRequest.get("/api/test")
                    .remoteAddress(new java.net.InetSocketAddress("10.0.0.1", 12345))
                    .build();

            StepVerifier.create(resolver.resolve(MockServerWebExchange.from(request)))
                    .assertNext(key -> {
                        assertThat(key).startsWith("rl:user:");
                        assertThat(key).contains("10.0.0.1");
                    })
                    .verifyComplete();
        }

        @Test
        @DisplayName("Authorization 头格式不正确 → 回退到 X-User-Id")
        void invalidAuthHeader_fallbackToUserId() {
            MockServerHttpRequest request = MockServerHttpRequest.get("/api/test")
                    .header("Authorization", "InvalidToken")
                    .header("X-User-Id", "99")
                    .build();

            StepVerifier.create(resolver.resolve(MockServerWebExchange.from(request)))
                    .assertNext(key -> assertThat(key).isEqualTo("rl:user:99"))
                    .verifyComplete();
        }
    }
}
