package com.ilbuy.gateway.ws;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * WebSocket 网关启动类
 *
 * <p>职责：
 * <ul>
 *   <li>管理客户端长连接（STOMP over WebSocket）</li>
 *   <li>维护用户→会话映射（Redis HASH，支持多实例部署）</li>
 *   <li>支持单播（点对点）和广播（主题订阅）消息推送</li>
 *   <li>WebSocket 握手时 JWT 鉴权（拒绝未授权连接）</li>
 *   <li>心跳检测 + 自动清理过期会话</li>
 * </ul>
 * </p>
 */
@SpringBootApplication
@EnableDiscoveryClient
@EnableScheduling
public class WebSocketGatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(WebSocketGatewayApplication.class, args);
    }
}
