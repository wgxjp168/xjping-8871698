package com.ilbuy.gateway.ws.handler;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.http.server.ServletServerHttpRequest;
import org.springframework.http.server.ServletServerHttpResponse;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.web.socket.WebSocketHandler;

import javax.crypto.SecretKey;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;

import static com.ilbuy.gateway.ws.handler.WebSocketAuthHandshakeInterceptor.*;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

/**
 * WebSocketAuthHandshakeInterceptor 单元测试
 */
@DisplayName("WebSocketAuthHandshakeInterceptor 单元测试")
@ExtendWith(MockitoExtension.class)
class WebSocketAuthHandshakeInterceptorTest {

    private static final String JWT_SECRET =
            "aWxidXktcGxhdGZvcm0tc2VjcmV0LWtleS0zMmJ5dGVz";
    private static final String ISSUER = "ilbuy-platform";

    private WebSocketAuthHandshakeInterceptor interceptor;
    private SecretKey secretKey;
    private WebSocketHandler wsHandler;

    @BeforeEach
    void setUp() throws Exception {
        interceptor = new WebSocketAuthHandshakeInterceptor();

        // 通过反射注入 @Value 字段（单元测试无 Spring 容器）
        var secretField = WebSocketAuthHandshakeInterceptor.class.getDeclaredField("jwtSecret");
        secretField.setAccessible(true);
        secretField.set(interceptor, JWT_SECRET);

        var issuerField = WebSocketAuthHandshakeInterceptor.class.getDeclaredField("jwtIssuer");
        issuerField.setAccessible(true);
        issuerField.set(interceptor, ISSUER);

        interceptor.init();

        byte[] keyBytes = Decoders.BASE64.decode(JWT_SECRET);
        secretKey  = Keys.hmacShaKeyFor(keyBytes);
        wsHandler  = mock(WebSocketHandler.class);
    }

    private String buildToken(long expireMs) {
        return Jwts.builder()
                .issuer(ISSUER)
                .subject("10001")
                .claim("userId",   10001L)
                .claim("username", "testUser")
                .claim("tenantId", "tenant001")
                .issuedAt(new Date())
                .expiration(new Date(System.currentTimeMillis() + expireMs))
                .signWith(secretKey, Jwts.SIG.HS256)
                .compact();
    }

    @Nested
    @DisplayName("Token 通过查询参数传递")
    class TokenViaQueryParam {

        @Test
        @DisplayName("有效 Token（查询参数）→ 握手通过，用户信息写入 attributes")
        void validTokenInQueryParam_handshakeAllowed() {
            String token = buildToken(3600_000);
            MockHttpServletRequest request = new MockHttpServletRequest("GET", "/ws");
            request.addParameter("token", token);

            Map<String, Object> attrs = new HashMap<>();
            boolean result = interceptor.beforeHandshake(
                    new ServletServerHttpRequest(request),
                    new ServletServerHttpResponse(new MockHttpServletResponse()),
                    wsHandler, attrs);

            assertThat(result).isTrue();
            assertThat(attrs.get(ATTR_USER_ID)).isEqualTo("10001");
            assertThat(attrs.get(ATTR_USERNAME)).isEqualTo("testUser");
            assertThat(attrs.get(ATTR_TENANT_ID)).isEqualTo("tenant001");
        }

        @Test
        @DisplayName("带 'Bearer ' 前缀的查询参数 Token → 自动去掉前缀，握手通过")
        void tokenWithBearerPrefix_handshakeAllowed() {
            String token = "Bearer " + buildToken(3600_000);
            MockHttpServletRequest request = new MockHttpServletRequest("GET", "/ws");
            request.addParameter("token", token);

            boolean result = interceptor.beforeHandshake(
                    new ServletServerHttpRequest(request),
                    new ServletServerHttpResponse(new MockHttpServletResponse()),
                    wsHandler, new HashMap<>());

            assertThat(result).isTrue();
        }
    }

    @Nested
    @DisplayName("Token 通过请求头传递")
    class TokenViaHeader {

        @Test
        @DisplayName("有效 Authorization 头 → 握手通过")
        void validAuthHeader_handshakeAllowed() {
            String token = buildToken(3600_000);
            MockHttpServletRequest request = new MockHttpServletRequest("GET", "/ws");
            request.addHeader("Authorization", "Bearer " + token);

            boolean result = interceptor.beforeHandshake(
                    new ServletServerHttpRequest(request),
                    new ServletServerHttpResponse(new MockHttpServletResponse()),
                    wsHandler, new HashMap<>());

            assertThat(result).isTrue();
        }

        @Test
        @DisplayName("过期 Token → 握手拒绝")
        void expiredToken_handshakeRejected() {
            String token = buildToken(-1000);  // 已过期
            MockHttpServletRequest request = new MockHttpServletRequest("GET", "/ws");
            request.addHeader("Authorization", "Bearer " + token);

            boolean result = interceptor.beforeHandshake(
                    new ServletServerHttpRequest(request),
                    new ServletServerHttpResponse(new MockHttpServletResponse()),
                    wsHandler, new HashMap<>());

            assertThat(result).isFalse();
        }
    }

    @Nested
    @DisplayName("无 Token 场景")
    class NoToken {

        @Test
        @DisplayName("无 Token → 握手拒绝")
        void noToken_handshakeRejected() {
            MockHttpServletRequest request = new MockHttpServletRequest("GET", "/ws");

            boolean result = interceptor.beforeHandshake(
                    new ServletServerHttpRequest(request),
                    new ServletServerHttpResponse(new MockHttpServletResponse()),
                    wsHandler, new HashMap<>());

            assertThat(result).isFalse();
        }

        @Test
        @DisplayName("伪造签名 Token → 握手拒绝")
        void tamperedToken_handshakeRejected() {
            MockHttpServletRequest request = new MockHttpServletRequest("GET", "/ws");
            request.addHeader("Authorization", "Bearer eyJhbGciOiJIUzI1NiJ9.fake.signature");

            boolean result = interceptor.beforeHandshake(
                    new ServletServerHttpRequest(request),
                    new ServletServerHttpResponse(new MockHttpServletResponse()),
                    wsHandler, new HashMap<>());

            assertThat(result).isFalse();
        }
    }
}
