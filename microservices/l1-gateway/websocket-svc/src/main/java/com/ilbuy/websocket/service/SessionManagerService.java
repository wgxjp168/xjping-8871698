package com.ilbuy.websocket.service;

import com.ilbuy.websocket.dto.SessionInfo;
import org.springframework.web.socket.WebSocketSession;

import java.util.List;
import java.util.Optional;

/**
 * WebSocket 会话管理服务接口
 */
public interface SessionManagerService {

    /**
     * 注册新连接
     */
    void register(WebSocketSession wsSession, String userId, String userType, String clientIp);

    /**
     * 移除断开的连接
     */
    void remove(String wsSessionId);

    /**
     * 按用户 ID 查找会话（一个用户可能有多端连接）
     */
    List<WebSocketSession> findByUserId(String userId);

    /**
     * 按 wsSessionId 查找会话信息
     */
    Optional<SessionInfo> getSessionInfo(String wsSessionId);

    /**
     * 获取当前在线连接数
     */
    int getOnlineCount();

    /**
     * 更新会话最后活跃时间
     */
    void refreshLastActive(String wsSessionId);

    /**
     * 向指定用户推送消息
     *
     * @return 发送成功的会话数量
     */
    int pushToUser(String userId, String jsonMessage);
}
