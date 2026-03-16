package com.ilbuy.order.model.enums;

/**
 * 订单状态机
 * PENDING → PAID → SHIPPED → DELIVERED
 *         ↘ CANCELLED
 */
public enum OrderStatus {
    PENDING,     // 待支付
    PAID,        // 已支付
    SHIPPED,     // 已发货
    DELIVERED,   // 已完成
    CANCELLED,   // 已取消
    REFUNDING,   // 退款中
    REFUNDED     // 已退款
}
