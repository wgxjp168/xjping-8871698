package com.ilbuy.gateway.ws.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

/**
 * WebSocket 消息载体
 *
 * <p>前后端通信统一消息格式，通过 STOMP 帧传输（JSON 序列化）。</p>
 *
 * <pre>示例（聊天消息）：
 * {
 *   "type":    "CHAT",
 *   "from":    "10001",
 *   "to":      "10002",
 *   "content": "你好！",
 *   "traceId": "a1b2c3d4..."
 * }
 * </pre>
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class WsMessage implements Serializable {

    /** 消息类型 */
    private MessageType type;

    /** 发送方用户 ID（系统推送时为 "system"） */
    private String from;

    /** 目标用户 ID（单播）；广播时为 null */
    private String to;

    /** 消息内容（可以是文本或 JSON 字符串） */
    private Object content;

    /** 链路追踪 ID */
    private String traceId;

    /** 消息时间戳（毫秒） */
    @Builder.Default
    private long timestamp = System.currentTimeMillis();

    // ──── 工厂方法 ────

    public static WsMessage system(MessageType type, Object content) {
        return WsMessage.builder()
                .type(type)
                .from("system")
                .content(content)
                .build();
    }

    public static WsMessage chat(String from, String to, Object content) {
        return WsMessage.builder()
                .type(MessageType.CHAT)
                .from(from)
                .to(to)
                .content(content)
                .build();
    }

    public static WsMessage pong() {
        return WsMessage.builder()
                .type(MessageType.PONG)
                .from("system")
                .content("pong")
                .build();
    }
}
