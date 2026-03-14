package com.ilbuy.common.core.exception;

import lombok.Getter;

/**
 * 全局错误码枚举
 */
@Getter
public enum ErrorCode {

    // 通用
    SUCCESS(200, "成功"),
    SYSTEM_ERROR(500, "系统异常"),
    PARAM_ERROR(400, "参数错误"),
    UNAUTHORIZED(401, "未授权"),
    FORBIDDEN(403, "无权限"),
    NOT_FOUND(404, "资源不存在"),
    TOO_MANY_REQUESTS(429, "请求过于频繁"),

    // 用户相关
    USER_NOT_FOUND(1001, "用户不存在"),
    USER_PASSWORD_ERROR(1002, "密码错误"),
    USER_DISABLED(1003, "账户已禁用"),
    TOKEN_EXPIRED(1004, "Token已过期"),
    TOKEN_INVALID(1005, "Token无效"),

    // 采购决策相关
    DECISION_TIMEOUT(2001, "AI决策超时"),
    DECISION_FAILED(2002, "AI决策失败"),
    PLATFORM_API_ERROR(2003, "电商平台API调用异常"),
    PRODUCT_NOT_FOUND(2004, "未找到匹配商品"),

    // 支付相关
    PAYMENT_FAILED(3001, "支付失败"),
    ORDER_NOT_FOUND(3002, "订单不存在"),

    // 报告相关
    REPORT_GENERATE_FAILED(4001, "报告生成失败"),
    REPORT_NOT_FOUND(4002, "报告不存在");

    private final int code;
    private final String message;

    ErrorCode(int code, String message) {
        this.code = code;
        this.message = message;
    }
}
