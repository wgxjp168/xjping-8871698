package com.ilbuy.websocket.service.impl;

import com.ilbuy.websocket.dto.SessionInfo;
import com.ilbuy.websocket.service.SessionManagerService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;

import java.io.IOException;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * WebSocket 会话管理服务实现
 *
 * <p>使用 ConcurrentHashMap 管理本节点连接。
 * 生产集群模式下需结合 Redis Pub/Sub 实现跨节点消息推送。
 *
 * @author ILbuy Team
 */
@Slf4j
@Service
public class SessionManagerServiceImpl implements SessionManagerService {

    /** wsSessionId → WebSocketSession */
    private final Map<String, WebSocketSession> sessionMap = new ConcurrentHashMap<>();

    /** wsSessionId → SessionInfo */
    private final Map<String, SessionInfo> sessionInfoMap = new ConcurrentHashMap<>();

    /** userId → Set<wsSessionId>（支持同一用户多端连接）*/
    private final Map<String, Set<String>> userSessionMap = new ConcurrentHashMap<>();

    @Override
    public void register(WebSocketSession wsSession, String userId, String userType, String clientIp) {
        String wsSessionId = wsSession.getId();

        sessionMap.put(wsSessionId, wsSession);
        sessionInfoMap.put(wsSessionId, SessionInfo.builder()
            .wsSessionId(wsSessionId)
            .userId(userId)
            .userType(userType)
            .clientIp(clientIp)
            .connectedAt(Instant.now())
            .lastActiveAt(Instant.now())
            .status("CONNECTED")
            .build());

        userSessionMap.computeIfAbsent(userId, k -> ConcurrentHashMap.newKeySet()).add(wsSessionId);

        log.info("[WS-连接] wsSessionId={} userId={} userType={} ip={} onlineCount={}",
            wsSessionId, userId, userType, clientIp, sessionMap.size());
    }

    @Override
    public void remove(String wsSessionId) {
        WebSocketSession removed = sessionMap.remove(wsSessionId);
        SessionInfo info = sessionInfoMap.remove(wsSessionId);

        if (info != null) {
            Set<String> userSessions = userSessionMap.get(info.getUserId());
            if (userSessions != null) {
                userSessions.remove(wsSessionId);
                if (userSessions.isEmpty()) {
                    userSessionMap.remove(info.getUserId());
                }
            }
            log.info("[WS-断开] wsSessionId={} userId={} onlineCount={}",
                wsSessionId, info.getUserId(), sessionMap.size());
        }
    }

    @Override
    public List<WebSocketSession> findByUserId(String userId) {
        Set<String> wsSessionIds = userSessionMap.get(userId);
        if (wsSessionIds == null || wsSessionIds.isEmpty()) {
            return Collections.emptyList();
        }
        return wsSessionIds.stream()
            .map(sessionMap::get)
            .filter(Objects::nonNull)
            .filter(WebSocketSession::isOpen)
            .collect(Collectors.toList());
    }

    @Override
    public Optional<SessionInfo> getSessionInfo(String wsSessionId) {
        return Optional.ofNullable(sessionInfoMap.get(wsSessionId));
    }

    @Override
    public int getOnlineCount() {
        return sessionMap.size();
    }

    @Override
    public void refreshLastActive(String wsSessionId) {
        SessionInfo info = sessionInfoMap.get(wsSessionId);
        if (info != null) {
            info.setLastActiveAt(Instant.now());
        }
    }

    @Override
    public int pushToUser(String userId, String jsonMessage) {
        List<WebSocketSession> sessions = findByUserId(userId);
        int successCount = 0;
        for (WebSocketSession session : sessions) {
            try {
                if (session.isOpen()) {
                    session.sendMessage(new TextMessage(jsonMessage));
                    successCount++;
                }
            } catch (IOException e) {
                log.error("[WS-推送失败] wsSessionId={} userId={} error={}",
                    session.getId(), userId, e.getMessage());
            }
        }
        return successCount;
    }
}
