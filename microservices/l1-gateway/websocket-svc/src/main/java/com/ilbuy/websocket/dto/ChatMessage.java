package com.ilbuy.websocket.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * WebSocket 消息 DTO
 *
 * <p>消息类型（type）说明：
 * <ul>
 *   <li>TEXT    - L0 文本输入</li>
 *   <li>VOICE   - L0 语音输入（base64 音频数据）</li>
 *   <li>IMAGE   - L0 图片输入（base64 图片数据）</li>
 *   <li>LINK    - L0 商品链接输入</li>
 *   <li>REPLY   - 服务端推送回复</li>
 *   <li>TYPING  - 打字中提示</li>
 *   <li>DONE    - 流式回复结束标志</li>
 *   <li>ERROR   - 服务端错误通知</li>
 *   <li>PING    - 心跳检测</li>
 *   <li>PONG    - 心跳响应</li>
 * </ul>
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ChatMessage {

    /** 消息类型 */
    private String type;

    /** 会话 ID（客户端生成）*/
    private String sessionId;

    /** 消息 ID（用于去重）*/
    private String messageId;

    /** 消息内容（文本 / base64 编码的语音或图片）*/
    private String content;

    /** 媒体类型（语音: audio/wav；图片: image/jpeg 等）*/
    private String mediaType;

    /** L2 对话管理返回的 AI 回复（流式时为分段内容）*/
    private String aiReply;

    /** 是否为流式最后一帧 */
    private Boolean lastChunk;

    /** 时间戳 */
    private Long timestamp;

    /** 错误码（type=ERROR 时有值）*/
    private Integer errorCode;

    /** 错误描述（type=ERROR 时有值）*/
    private String errorMessage;

    // ============ 工厂方法 ============

    public static ChatMessage pong() {
        return ChatMessage.builder().type("PONG").timestamp(System.currentTimeMillis()).build();
    }

    public static ChatMessage typing(String sessionId) {
        return ChatMessage.builder().type("TYPING").sessionId(sessionId)
            .timestamp(System.currentTimeMillis()).build();
    }

    public static ChatMessage done(String sessionId) {
        return ChatMessage.builder().type("DONE").sessionId(sessionId)
            .timestamp(System.currentTimeMillis()).build();
    }

    public static ChatMessage error(int code, String message) {
        return ChatMessage.builder().type("ERROR").errorCode(code).errorMessage(message)
            .timestamp(System.currentTimeMillis()).build();
    }

    public static ChatMessage reply(String sessionId, String content, boolean lastChunk) {
        return ChatMessage.builder().type("REPLY").sessionId(sessionId)
            .aiReply(content).lastChunk(lastChunk)
            .timestamp(System.currentTimeMillis()).build();
    }
}
