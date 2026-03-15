package com.ilbuy.websocket;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.cloud.openfeign.EnableFeignClients;

/**
 * ILbuy WebSocket 实时会话服务启动类（端口 8002）
 *
 * <p>负责：WebSocket 长连接管理、多模态消息分发（文本/语音）、L2 对话管理服务对接预留
 *
 * <p>数据流转：
 * <pre>
 *   L0 TEXT_IN / VOICE_IN  ──→  WS连接  ──→  ChatWebSocketHandler  ──→  L2 conversation-svc（预留）
 * </pre>
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@SpringBootApplication
@EnableDiscoveryClient
@EnableFeignClients
public class WebSocketServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(WebSocketServiceApplication.class, args);
    }
}
