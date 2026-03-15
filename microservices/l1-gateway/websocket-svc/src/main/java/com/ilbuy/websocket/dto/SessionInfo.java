package com.ilbuy.websocket.dto;

import lombok.Builder;
import lombok.Data;

import java.time.Instant;

/**
 * WebSocket 会话信息
 */
@Data
@Builder
public class SessionInfo {

    /** 内部 WebSocket Session ID */
    private String wsSessionId;

    /** 业务会话 ID（由客户端生成，用于 L2 对话上下文关联）*/
    private String sessionId;

    /** 用户 ID */
    private String userId;

    /** 用户类型（BUSINESS / CONSUMER）*/
    private String userType;

    /** 客户端 IP */
    private String clientIp;

    /** 连接建立时间 */
    private Instant connectedAt;

    /** 最后活跃时间 */
    private Instant lastActiveAt;

    /** 连接状态 */
    private String status; // CONNECTED / DISCONNECTED
}
