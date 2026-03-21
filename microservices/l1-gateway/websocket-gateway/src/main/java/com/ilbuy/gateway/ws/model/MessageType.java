package com.ilbuy.gateway.ws.model;

/**
 * WebSocket 消息类型枚举
 */
public enum MessageType {

    /** 握手成功通知 */
    CONNECTED,

    /** 聊天消息（C2C / C2S） */
    CHAT,

    /** AI 对话回复（流式/批量） */
    AI_REPLY,

    /** 订单状态变更推送 */
    ORDER_UPDATE,

    /** 系统通知（广播） */
    NOTIFICATION,

    /** 心跳 Ping */
    PING,

    /** 心跳 Pong */
    PONG,

    /** 错误消息 */
    ERROR,

    /** 连接关闭通知 */
    DISCONNECTED
}
