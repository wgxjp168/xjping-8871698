package com.ilbuy.gateway.ws.handler;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.http.server.ServletServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.server.HandshakeInterceptor;

import javax.crypto.SecretKey;
import java.util.Map;

/**
 * WebSocket 握手鉴权拦截器
 *
 * <p>客户端连接时携带 JWT Token（两种方式任选其一）：
 * <ol>
 *   <li>查询参数：{@code ws://host/ws?token=Bearer_xxx}</li>
 *   <li>请求头：{@code Authorization: Bearer xxx}（部分客户端不支持 WS 自定义头）</li>
 * </ol>
 * </p>
 *
 * <p>鉴权通过后，将 userId/username 写入 WebSocket Session attributes，
 * 供 {@link WebSocketMessageHandler} 使用。</p>
 */
@Slf4j
@Component
public class WebSocketAuthHandshakeInterceptor implements HandshakeInterceptor {

    public static final String ATTR_USER_ID   = "userId";
    public static final String ATTR_USERNAME  = "username";
    public static final String ATTR_TENANT_ID = "tenantId";
    public static final String ATTR_TRACE_ID  = "traceId";

    private static final String CLAIM_USER_ID   = "userId";
    private static final String CLAIM_USERNAME  = "username";
    private static final String CLAIM_TENANT_ID = "tenantId";

    @Value("${ilbuy.gateway.jwt.secret}")
    private String jwtSecret;

    @Value("${ilbuy.gateway.jwt.issuer:ilbuy-platform}")
    private String jwtIssuer;

    private SecretKey secretKey;

    @PostConstruct
    public void init() {
        byte[] keyBytes = Decoders.BASE64.decode(jwtSecret);
        this.secretKey  = Keys.hmacShaKeyFor(keyBytes);
    }

    @Override
    public boolean beforeHandshake(ServerHttpRequest request, ServerHttpResponse response,
                                   WebSocketHandler wsHandler, Map<String, Object> attributes) {
        String token = resolveToken(request);
        if (token == null) {
            log.warn("[WS Auth] 拒绝握手：缺少 Token uri={}", request.getURI());
            return false;
        }

        try {
            Claims claims = Jwts.parser()
                    .verifyWith(secretKey)
                    .requireIssuer(jwtIssuer)
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();

            // 将用户信息写入 Session 属性（后续 Handler 直接读取）
            attributes.put(ATTR_USER_ID,   String.valueOf(claims.get(CLAIM_USER_ID)));
            attributes.put(ATTR_USERNAME,  claims.get(CLAIM_USERNAME, String.class));
            attributes.put(ATTR_TENANT_ID, claims.get(CLAIM_TENANT_ID, String.class));

            log.info("[WS Auth] 握手鉴权通过 userId={} uri={}",
                    claims.get(CLAIM_USER_ID), request.getURI());
            return true;

        } catch (ExpiredJwtException e) {
            log.warn("[WS Auth] 拒绝握手：Token 已过期 uri={}", request.getURI());
            return false;
        } catch (JwtException e) {
            log.warn("[WS Auth] 拒绝握手：Token 无效 uri={} err={}", request.getURI(), e.getMessage());
            return false;
        }
    }

    @Override
    public void afterHandshake(ServerHttpRequest request, ServerHttpResponse response,
                                WebSocketHandler wsHandler, Exception exception) {
        // 握手后无需额外处理
    }

    private String resolveToken(ServerHttpRequest request) {
        // 1. 查询参数（客户端 WebSocket API 无法设置自定义 Header 时使用）
        if (request instanceof ServletServerHttpRequest servletRequest) {
            String tokenParam = servletRequest.getServletRequest().getParameter("token");
            if (tokenParam != null && !tokenParam.isBlank()) {
                return tokenParam.startsWith("Bearer ") ? tokenParam.substring(7) : tokenParam;
            }
        }

        // 2. Authorization 请求头
        String authHeader = request.getHeaders().getFirst("Authorization");
        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            return authHeader.substring(7);
        }

        return null;
    }
}
