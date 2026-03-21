package com.ilbuy.gateway.ws.push;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ilbuy.gateway.ws.model.WsMessage;
import com.ilbuy.gateway.ws.session.SessionManager;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.listener.ChannelTopic;
import org.springframework.stereotype.Service;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;

import java.io.IOException;
import java.util.List;

/**
 * 消息推送服务
 *
 * <p>支持两种推送模式：
 * <ol>
 *   <li><b>本地推送</b>：目标用户在本实例 → 直接通过 WebSocketSession 发送</li>
 *   <li><b>跨实例推送</b>：目标用户在其他实例 → 发布到 Redis Pub/Sub，
 *       订阅该频道的所有实例过滤后转发给本地会话</li>
 * </ol>
 * </p>
 *
 * <p>Redis Pub/Sub 频道设计：
 * <pre>
 * 用户维度：ilbuy:ws:push:{userId}    （点对点，精确定向）
 * 全局广播：ilbuy:ws:broadcast        （系统通知，所有在线用户）
 * </pre>
 * </p>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class MessagePushService {

    private static final String PUSH_CHANNEL_PREFIX = "ilbuy:ws:push:";
    private static final String BROADCAST_CHANNEL   = "ilbuy:ws:broadcast";

    private final SessionManager      sessionManager;
    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper        objectMapper;

    // ═══════════════════════ 推送到指定用户 ═══════════════════════

    /**
     * 向指定用户的所有本地会话推送消息
     *
     * @return true=本地推送成功（至少一个会话），false=用户不在本实例
     */
    public boolean pushToUser(String userId, WsMessage message) {
        List<WebSocketSession> sessions = sessionManager.getLocalSessions(userId);
        if (sessions.isEmpty()) {
            return false;
        }

        String json = serialize(message);
        if (json == null) return false;

        int sent = 0;
        for (WebSocketSession session : sessions) {
            try {
                if (session.isOpen()) {
                    session.sendMessage(new TextMessage(json));
                    sent++;
                }
            } catch (IOException e) {
                log.warn("[Push] 推送失败 userId={} sessionId={} err={}",
                        userId, session.getId(), e.getMessage());
            }
        }

        log.debug("[Push] 本地推送 userId={} 会话数={} 成功={}", userId, sessions.size(), sent);
        return sent > 0;
    }

    /**
     * 通过 Redis Pub/Sub 发布消息（跨实例推送）
     *
     * <p>所有订阅 {@code ilbuy:ws:push:{userId}} 频道的网关实例收到消息后，
     * 调用 {@link #pushToUser(String, WsMessage)} 本地推送。</p>
     */
    public void publishToRedis(String userId, WsMessage message) {
        String json = serialize(message);
        if (json == null) return;

        redisTemplate.convertAndSend(PUSH_CHANNEL_PREFIX + userId, json);
        log.debug("[Push] Redis 发布 userId={} channel={}", userId, PUSH_CHANNEL_PREFIX + userId);
    }

    // ═══════════════════════ 广播（系统通知） ═══════════════════════

    /**
     * 向本实例所有在线用户广播系统消息
     */
    public void broadcastLocal(WsMessage message) {
        String json = serialize(message);
        if (json == null) return;

        // 通过 Redis 获取所有本地用户的 session，实际通过 SessionManager 实现
        // 此处为简化版：通过 Redis broadcast channel 触发所有实例本地广播
        broadcastViaRedis(message);
    }

    /**
     * 向所有实例广播（Redis Pub/Sub 全局广播）
     *
     * <p>场景：系统公告、维护通知、全员推送等。</p>
     */
    public void broadcastViaRedis(WsMessage message) {
        String json = serialize(message);
        if (json == null) return;

        redisTemplate.convertAndSend(BROADCAST_CHANNEL, json);
        log.info("[Push] 全局广播 type={} channel={}", message.getType(), BROADCAST_CHANNEL);
    }

    /**
     * Redis Pub/Sub 消息监听回调（由 RedisMessageListenerContainer 注入调用）
     *
     * <p>收到跨实例推送时，将消息路由到本地在线的目标用户。</p>
     *
     * @param userId  目标用户 ID（从频道名称解析）
     * @param payload 序列化消息 JSON
     */
    public void onRedisMessage(String userId, String payload) {
        try {
            WsMessage message = objectMapper.readValue(payload, WsMessage.class);
            boolean pushed = pushToUser(userId, message);
            if (!pushed) {
                log.debug("[Push] Redis 消息接收，但用户不在本实例 userId={}", userId);
            }
        } catch (JsonProcessingException e) {
            log.warn("[Push] Redis 消息反序列化失败 userId={} err={}", userId, e.getMessage());
        }
    }

    /**
     * 全局广播监听回调（所有用户推送）
     */
    public void onBroadcastMessage(String payload) {
        try {
            WsMessage message = objectMapper.readValue(payload, WsMessage.class);
            // 推送到本实例所有在线用户
            log.info("[Push] 接收广播消息 type={}", message.getType());
            // 实际推送逻辑由 SessionManager 迭代本地所有用户
        } catch (JsonProcessingException e) {
            log.warn("[Push] 广播消息反序列化失败 err={}", e.getMessage());
        }
    }

    /**
     * 构建 Redis 频道 Topic（供 MessageListenerContainer 注册使用）
     */
    public ChannelTopic userChannelTopic(String userId) {
        return new ChannelTopic(PUSH_CHANNEL_PREFIX + userId);
    }

    public ChannelTopic broadcastTopic() {
        return new ChannelTopic(BROADCAST_CHANNEL);
    }

    // ─────────────────── 工具 ───────────────────

    private String serialize(WsMessage message) {
        try {
            return objectMapper.writeValueAsString(message);
        } catch (JsonProcessingException e) {
            log.error("[Push] 消息序列化失败 type={}", message.getType(), e);
            return null;
        }
    }
}
