package com.ilbuy.gateway.ws.session;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.WebSocketSession;

import java.time.Duration;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * WebSocket 会话管理器
 *
 * <p>双层存储策略：
 * <ul>
 *   <li>本地 ConcurrentHashMap：存储当前实例的 WebSocketSession 引用（不可序列化，只能本地）</li>
 *   <li>Redis HASH：存储全局用户→instanceId 映射，支持跨实例路由消息</li>
 * </ul>
 * </p>
 *
 * <p>数据结构：
 * <pre>
 * Redis Key:  ilbuy:ws:sessions:{userId}
 * Redis Type: HASH
 *   field: {sessionId}
 *   value: {instanceId}:{连接时间戳}
 * TTL: 25 小时（稍长于最长 Refresh Token 有效期，心跳会滚动续期）
 * </pre>
 * </p>
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class SessionManager {

    private static final String SESSION_KEY_PREFIX = "ilbuy:ws:sessions:";
    private static final Duration SESSION_TTL      = Duration.ofHours(25);

    /** 本地会话表：sessionId → WebSocketSession */
    private final Map<String, WebSocketSession> localSessions = new ConcurrentHashMap<>();

    /** 用户→会话 ID 集合（本地索引，用于按 userId 快速查找本地 session） */
    private final Map<String, Set<String>> userLocalSessions = new ConcurrentHashMap<>();

    private final StringRedisTemplate redisTemplate;
    private final String instanceId = UUID.randomUUID().toString().substring(0, 8);

    // ═══════════════════════ 注册/注销 ═══════════════════════

    /**
     * 注册新连接
     *
     * @param session WebSocket 会话
     * @param userId  已认证用户 ID
     */
    public void register(WebSocketSession session, String userId) {
        String sessionId = session.getId();

        // 本地缓存
        localSessions.put(sessionId, session);
        userLocalSessions.computeIfAbsent(userId, k -> ConcurrentHashMap.newKeySet())
                .add(sessionId);

        // Redis 全局注册
        String redisKey = SESSION_KEY_PREFIX + userId;
        redisTemplate.opsForHash().put(redisKey, sessionId, instanceId + ":" + System.currentTimeMillis());
        redisTemplate.expire(redisKey, SESSION_TTL);

        log.info("[WS] 会话注册 userId={} sessionId={} instance={} 在线数={}",
                userId, sessionId, instanceId, localSessions.size());
    }

    /**
     * 注销会话（连接断开时调用）
     *
     * @param session WebSocket 会话
     * @param userId  用户 ID（可能为 null，如握手失败）
     */
    public void unregister(WebSocketSession session, String userId) {
        String sessionId = session.getId();

        // 本地清理
        localSessions.remove(sessionId);
        if (userId != null) {
            Set<String> sessions = userLocalSessions.get(userId);
            if (sessions != null) {
                sessions.remove(sessionId);
                if (sessions.isEmpty()) {
                    userLocalSessions.remove(userId);
                }
            }
        }

        // Redis 清理
        if (userId != null) {
            String redisKey = SESSION_KEY_PREFIX + userId;
            redisTemplate.opsForHash().delete(redisKey, sessionId);
        }

        log.info("[WS] 会话注销 userId={} sessionId={} 剩余在线={}",
                userId, sessionId, localSessions.size());
    }

    // ═══════════════════════ 查询 ═══════════════════════

    /**
     * 获取用户在本实例上的所有 WebSocket 会话（用于本地推送）
     */
    public List<WebSocketSession> getLocalSessions(String userId) {
        Set<String> sessionIds = userLocalSessions.getOrDefault(userId, Collections.emptySet());
        List<WebSocketSession> result = new ArrayList<>();
        for (String sid : sessionIds) {
            WebSocketSession ws = localSessions.get(sid);
            if (ws != null && ws.isOpen()) {
                result.add(ws);
            }
        }
        return result;
    }

    /**
     * 获取用户在所有实例上的会话 ID（用于跨实例路由判断）
     */
    public Map<Object, Object> getGlobalSessions(String userId) {
        return redisTemplate.opsForHash().entries(SESSION_KEY_PREFIX + userId);
    }

    /**
     * 用户是否在线（本实例或其他实例）
     */
    public boolean isOnline(String userId) {
        Long count = redisTemplate.opsForHash().size(SESSION_KEY_PREFIX + userId);
        return count != null && count > 0;
    }

    /**
     * 当前实例在线连接数
     */
    public int localConnectionCount() {
        return localSessions.size();
    }

    /**
     * 会话续期（心跳时调用，防止 TTL 过期）
     */
    public void refresh(String userId) {
        redisTemplate.expire(SESSION_KEY_PREFIX + userId, SESSION_TTL);
    }

    /**
     * 按 sessionId 获取本地会话
     */
    public Optional<WebSocketSession> getLocalSession(String sessionId) {
        WebSocketSession ws = localSessions.get(sessionId);
        return (ws != null && ws.isOpen()) ? Optional.of(ws) : Optional.empty();
    }

    public String getInstanceId() {
        return instanceId;
    }
}
