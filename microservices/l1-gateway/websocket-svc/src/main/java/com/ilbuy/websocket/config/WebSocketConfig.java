package com.ilbuy.websocket.config;

import com.ilbuy.websocket.handler.ChatHandshakeInterceptor;
import com.ilbuy.websocket.handler.ChatWebSocketHandler;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

/**
 * WebSocket 配置
 *
 * <p>端点：
 * <ul>
 *   <li>{@code /ws/chat}    - 主聊天入口（文本/语音/图片/链接）</li>
 *   <li>{@code /ws/status}  - 连接状态查询（HTTP，见 WebSocketStatusController）</li>
 * </ul>
 *
 * <p>客户端连接示例：
 * <pre>ws://localhost:8002/ws/chat?token=eyJhbGciOiJIUzI1NiJ9...</pre>
 */
@Configuration
@EnableWebSocket
@EnableAsync
@RequiredArgsConstructor
public class WebSocketConfig implements WebSocketConfigurer {

    private final ChatWebSocketHandler chatWebSocketHandler;
    private final ChatHandshakeInterceptor chatHandshakeInterceptor;

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(chatWebSocketHandler, "/ws/chat")
            .addInterceptors(chatHandshakeInterceptor)
            .setAllowedOriginPatterns("*");   // 生产环境指定具体域名
    }
}
