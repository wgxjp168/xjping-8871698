package com.ilbuy.gateway.ws.config;

import com.ilbuy.gateway.ws.handler.WebSocketAuthHandshakeInterceptor;
import com.ilbuy.gateway.ws.handler.WebSocketMessageHandler;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

/**
 * WebSocket 端点注册配置
 *
 * <p>端点设计：
 * <ul>
 *   <li>{@code /ws}          — 主 WebSocket 端点（前端通用）</li>
 *   <li>{@code /ws/dialog}   — AI 对话专用（高优先级）</li>
 *   <li>{@code /ws/notify}   — 通知推送专用（只读）</li>
 * </ul>
 * </p>
 *
 * <p>注意：此处使用原生 WebSocket（非 STOMP），支持所有客户端类型。
 * 若需 STOMP 协议支持，改用 {@link StompWebSocketConfig}。</p>
 */
@Configuration
@EnableWebSocket
@RequiredArgsConstructor
public class WebSocketConfig implements WebSocketConfigurer {

    private final WebSocketMessageHandler            messageHandler;
    private final WebSocketAuthHandshakeInterceptor  authInterceptor;

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        // 主端点（带 JWT 鉴权 + SockJS 降级支持）
        registry.addHandler(messageHandler, "/ws", "/ws/dialog", "/ws/notify")
                .addInterceptors(authInterceptor)
                .setAllowedOriginPatterns("*");   // 生产改为实际前端域名
    }
}
