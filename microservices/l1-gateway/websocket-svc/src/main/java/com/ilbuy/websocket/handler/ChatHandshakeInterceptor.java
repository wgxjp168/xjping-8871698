package com.ilbuy.websocket.handler;

import com.ilbuy.websocket.config.JwtProperties;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.server.HandshakeInterceptor;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Map;

/**
 * WebSocket 握手拦截器（JWT 鉴权）
 *
 * <p>客户端通过 Query Param 传递 Token：
 * <pre>ws://host/ws/chat?token=eyJ...</pre>
 *
 * <p>鉴权通过后将 userId / userType 写入 WebSocket Session 属性，
 * 供 {@link ChatWebSocketHandler} 使用。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ChatHandshakeInterceptor implements HandshakeInterceptor {

    private final JwtProperties jwtProperties;

    @Override
    public boolean beforeHandshake(ServerHttpRequest request, ServerHttpResponse response,
                                   WebSocketHandler wsHandler, Map<String, Object> attributes) {
        String query = request.getURI().getQuery();
        String token = extractToken(query);

        if (token == null) {
            log.warn("[WS-握手拒绝] 缺少 token 参数");
            return false;
        }

        try {
            SecretKey key = Keys.hmacShaKeyFor(
                jwtProperties.getSecret().getBytes(StandardCharsets.UTF_8));
            Claims claims = Jwts.parser().verifyWith(key).build()
                .parseSignedClaims(token).getPayload();

            String userId = claims.getSubject();
            String userType = claims.get("userType", String.class);

            attributes.put("userId", userId);
            attributes.put("userType", userType != null ? userType : "CONSUMER");

            // 提取客户端 IP
            String xff = request.getHeaders().getFirst("X-Forwarded-For");
            String clientIp = (xff != null && !xff.isEmpty()) ? xff.split(",")[0].trim()
                : request.getRemoteAddress() != null
                    ? request.getRemoteAddress().getAddress().getHostAddress()
                    : "unknown";
            attributes.put("clientIp", clientIp);

            log.debug("[WS-握手通过] userId={} userType={}", userId, userType);
            return true;

        } catch (JwtException e) {
            log.warn("[WS-握手拒绝] Token 无效: {}", e.getMessage());
            return false;
        }
    }

    @Override
    public void afterHandshake(ServerHttpRequest request, ServerHttpResponse response,
                               WebSocketHandler wsHandler, Exception exception) {
        // no-op
    }

    private String extractToken(String query) {
        if (query == null) return null;
        for (String param : query.split("&")) {
            if (param.startsWith("token=")) {
                return param.substring("token=".length());
            }
        }
        return null;
    }
}
