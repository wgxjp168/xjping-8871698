package com.ilbuy.websocket.handler;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ilbuy.websocket.dto.ChatMessage;
import com.ilbuy.websocket.service.SessionManagerService;
import com.ilbuy.websocket.service.L2ConversationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.*;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.util.Map;

/**
 * 聊天 WebSocket 处理器
 *
 * <p>数据流转：
 * <pre>
 *   L0 TEXT_IN  →  ws://host/ws/chat  →  handleTextMessage  →  L2 conversation-svc（预留 Feign）
 *   L0 VOICE_IN →  ws://host/ws/chat  →  handleTextMessage  →  multimodal-input-svc（Feign）
 *   L2 AI Reply →  pushToUser  →  WebSocket 推送客户端
 * </pre>
 *
 * <p>连接鉴权：握手阶段由 {@link ChatHandshakeInterceptor} 从 Query Param token 验证 JWT。
 *
 * @author ILbuy Team
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ChatWebSocketHandler extends TextWebSocketHandler {

    private final SessionManagerService sessionManager;
    private final L2ConversationService conversationService;
    private final ObjectMapper objectMapper;

    /** WebSocket Session 属性 Key */
    private static final String ATTR_USER_ID = "userId";
    private static final String ATTR_USER_TYPE = "userType";
    private static final String ATTR_CLIENT_IP = "clientIp";

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        Map<String, Object> attrs = session.getAttributes();
        String userId = (String) attrs.get(ATTR_USER_ID);
        String userType = (String) attrs.get(ATTR_USER_TYPE);
        String clientIp = (String) attrs.getOrDefault(ATTR_CLIENT_IP, "unknown");

        sessionManager.register(session, userId, userType, clientIp);
        log.debug("[WS] 连接建立 wsId={} userId={}", session.getId(), userId);
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage textMessage) {
        sessionManager.refreshLastActive(session.getId());

        ChatMessage message;
        try {
            message = objectMapper.readValue(textMessage.getPayload(), ChatMessage.class);
        } catch (Exception e) {
            sendMessage(session, ChatMessage.error(400, "消息格式错误，请发送 JSON"));
            return;
        }

        String userId = (String) session.getAttributes().get(ATTR_USER_ID);
        log.debug("[WS-MSG] userId={} type={} sessionId={}", userId, message.getType(), message.getSessionId());

        switch (message.getType()) {
            case "PING" -> sendMessage(session, ChatMessage.pong());
            case "TEXT"  -> handleTextInput(session, message, userId);
            case "VOICE" -> handleVoiceInput(session, message, userId);
            case "IMAGE" -> handleImageInput(session, message, userId);
            case "LINK"  -> handleLinkInput(session, message, userId);
            default      -> sendMessage(session, ChatMessage.error(400, "未知消息类型: " + message.getType()));
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        sessionManager.remove(session.getId());
        log.debug("[WS] 连接关闭 wsId={} status={}", session.getId(), status);
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable exception) {
        log.error("[WS-ERROR] wsId={} error={}", session.getId(), exception.getMessage());
        sessionManager.remove(session.getId());
    }

    // ============ 私有处理方法 ============

    /**
     * 处理文本输入（对接 L2 对话管理服务）
     */
    private void handleTextInput(WebSocketSession session, ChatMessage message, String userId) {
        if (message.getContent() == null || message.getContent().isBlank()) {
            sendMessage(session, ChatMessage.error(400, "消息内容不能为空"));
            return;
        }

        // 发送"正在思考"提示
        sendMessage(session, ChatMessage.typing(message.getSessionId()));

        // 调用 L2 对话管理服务（异步，当前为预留接口）
        conversationService.processText(userId, message.getSessionId(), message.getContent(),
            // 流式回调：每个 AI 回复分段推送
            chunk -> {
                sendMessage(session, ChatMessage.reply(message.getSessionId(), chunk, false));
            },
            // 完成回调
            () -> {
                sendMessage(session, ChatMessage.done(message.getSessionId()));
            },
            // 错误回调
            errorMsg -> {
                sendMessage(session, ChatMessage.error(500, errorMsg));
            }
        );
    }

    /**
     * 处理语音输入（L0 VOICE_IN → multimodal-input-svc → L2）
     */
    private void handleVoiceInput(WebSocketSession session, ChatMessage message, String userId) {
        if (message.getContent() == null) {
            sendMessage(session, ChatMessage.error(400, "语音数据不能为空"));
            return;
        }
        sendMessage(session, ChatMessage.typing(message.getSessionId()));
        // 预留：调用 multimodal-input-svc 进行语音识别 → 转文本 → 再走 handleTextInput
        conversationService.processVoice(userId, message.getSessionId(), message.getContent(),
            message.getMediaType(),
            chunk -> sendMessage(session, ChatMessage.reply(message.getSessionId(), chunk, false)),
            () -> sendMessage(session, ChatMessage.done(message.getSessionId())),
            errorMsg -> sendMessage(session, ChatMessage.error(500, errorMsg))
        );
    }

    /**
     * 处理图片输入（L0 图片解析）
     */
    private void handleImageInput(WebSocketSession session, ChatMessage message, String userId) {
        sendMessage(session, ChatMessage.typing(message.getSessionId()));
        conversationService.processImage(userId, message.getSessionId(), message.getContent(),
            message.getMediaType(),
            chunk -> sendMessage(session, ChatMessage.reply(message.getSessionId(), chunk, false)),
            () -> sendMessage(session, ChatMessage.done(message.getSessionId())),
            errorMsg -> sendMessage(session, ChatMessage.error(500, errorMsg))
        );
    }

    /**
     * 处理商品链接输入
     */
    private void handleLinkInput(WebSocketSession session, ChatMessage message, String userId) {
        sendMessage(session, ChatMessage.typing(message.getSessionId()));
        conversationService.processLink(userId, message.getSessionId(), message.getContent(),
            chunk -> sendMessage(session, ChatMessage.reply(message.getSessionId(), chunk, false)),
            () -> sendMessage(session, ChatMessage.done(message.getSessionId())),
            errorMsg -> sendMessage(session, ChatMessage.error(500, errorMsg))
        );
    }

    private void sendMessage(WebSocketSession session, ChatMessage message) {
        if (!session.isOpen()) return;
        try {
            session.sendMessage(new TextMessage(objectMapper.writeValueAsString(message)));
        } catch (IOException e) {
            log.error("[WS-SEND] 发送失败 wsId={} error={}", session.getId(), e.getMessage());
        }
    }
}
