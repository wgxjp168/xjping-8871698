package com.ilbuy.gateway.ws.handler;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ilbuy.gateway.ws.model.MessageType;
import com.ilbuy.gateway.ws.model.WsMessage;
import com.ilbuy.gateway.ws.push.MessagePushService;
import com.ilbuy.gateway.ws.session.HeartbeatScheduler;
import com.ilbuy.gateway.ws.session.SessionManager;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import static com.ilbuy.gateway.ws.handler.WebSocketAuthHandshakeInterceptor.*;

/**
 * WebSocket 消息处理器
 *
 * <p>处理所有 WebSocket 文本帧：
 * <ul>
 *   <li>{@code PING}   → 回复 PONG，更新心跳时间戳</li>
 *   <li>{@code CHAT}   → 点对点消息路由（优先本地，否则 Redis Pub/Sub 跨实例）</li>
 *   <li>其他消息类型   → 转发至对应下游服务处理</li>
 * </ul>
 * </p>
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class WebSocketMessageHandler extends TextWebSocketHandler {

    private final SessionManager      sessionManager;
    private final HeartbeatScheduler  heartbeatScheduler;
    private final MessagePushService  messagePushService;
    private final ObjectMapper        objectMapper;

    // ═══════════════════════ 生命周期 ═══════════════════════

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        String userId = (String) session.getAttributes().get(ATTR_USER_ID);

        sessionManager.register(session, userId);
        heartbeatScheduler.initSession(session.getId());

        // 推送连接成功通知
        WsMessage connected = WsMessage.builder()
                .type(MessageType.CONNECTED)
                .from("system")
                .content("连接成功，欢迎 " + session.getAttributes().get(ATTR_USERNAME))
                .build();
        sendToSession(session, connected);

        log.info("[WS] 连接建立 userId={} sessionId={}", userId, session.getId());
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        String userId = (String) session.getAttributes().get(ATTR_USER_ID);

        sessionManager.unregister(session, userId);
        heartbeatScheduler.removeSession(session.getId());

        log.info("[WS] 连接关闭 userId={} sessionId={} status={}", userId, session.getId(), status);
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable exception) {
        String userId = (String) session.getAttributes().get(ATTR_USER_ID);
        log.warn("[WS] 传输错误 userId={} sessionId={} err={}",
                userId, session.getId(), exception.getMessage());
        sessionManager.unregister(session, userId);
        heartbeatScheduler.removeSession(session.getId());
    }

    // ═══════════════════════ 消息处理 ═══════════════════════

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        String userId = (String) session.getAttributes().get(ATTR_USER_ID);

        WsMessage wsMessage;
        try {
            wsMessage = objectMapper.readValue(message.getPayload(), WsMessage.class);
        } catch (Exception e) {
            log.warn("[WS] 消息解析失败 userId={} payload={}", userId, message.getPayload());
            sendError(session, "消息格式错误，请使用 JSON 格式");
            return;
        }

        wsMessage.setFrom(userId); // 强制覆盖发送方（防止伪造）

        switch (wsMessage.getType()) {
            case PING -> handlePing(session, userId);
            case CHAT -> handleChat(session, wsMessage, userId);
            default   -> log.debug("[WS] 未处理消息类型 type={} userId={}", wsMessage.getType(), userId);
        }
    }

    // ═══════════════════════ 各类消息处理 ═══════════════════════

    private void handlePing(WebSocketSession session, String userId) {
        heartbeatScheduler.recordPong(session.getId(), userId);
        sendToSession(session, WsMessage.pong());
    }

    private void handleChat(WebSocketSession session, WsMessage message, String fromUserId) {
        String toUserId = message.getTo();
        if (toUserId == null || toUserId.isBlank()) {
            sendError(session, "聊天消息缺少目标用户 ID");
            return;
        }

        // 尝试本地推送（同一实例）
        boolean sent = messagePushService.pushToUser(toUserId, message);
        if (!sent) {
            log.debug("[WS] 目标用户不在本实例，通过 Redis Pub/Sub 广播 toUser={}", toUserId);
            messagePushService.publishToRedis(toUserId, message);
        }

        // 给发送方回显确认
        WsMessage ack = WsMessage.builder()
                .type(MessageType.CHAT)
                .from("system")
                .to(fromUserId)
                .content("消息已发送")
                .build();
        sendToSession(session, ack);
    }

    // ═══════════════════════ 工具方法 ═══════════════════════

    private void sendToSession(WebSocketSession session, WsMessage message) {
        if (!session.isOpen()) return;
        try {
            String json = objectMapper.writeValueAsString(message);
            session.sendMessage(new TextMessage(json));
        } catch (Exception e) {
            log.warn("[WS] 消息发送失败 sessionId={} err={}", session.getId(), e.getMessage());
        }
    }

    private void sendError(WebSocketSession session, String errorMsg) {
        WsMessage error = WsMessage.builder()
                .type(MessageType.ERROR)
                .from("system")
                .content(errorMsg)
                .build();
        sendToSession(session, error);
    }
}
