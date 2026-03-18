package com.ilbuy.common.core.enums;

import lombok.Getter;
import lombok.RequiredArgsConstructor;

/**
 * 统一响应码枚举
 * <p>规范：1xx 系统级, 2xx 成功, 4xx 客户端错误, 5xx 服务端错误, 6xx 业务错误</p>
 */
@Getter
@RequiredArgsConstructor
public enum ResultCode {

    /* ===== 成功 ===== */
    SUCCESS(200, "操作成功"),
    CREATED(201, "创建成功"),
    NO_CONTENT(204, "无内容"),

    /* ===== 客户端错误 ===== */
    BAD_REQUEST(400, "请求参数错误"),
    UNAUTHORIZED(401, "未授权，请先登录"),
    FORBIDDEN(403, "无权限访问"),
    NOT_FOUND(404, "资源不存在"),
    METHOD_NOT_ALLOWED(405, "请求方法不允许"),
    CONFLICT(409, "资源冲突"),
    TOO_MANY_REQUESTS(429, "请求过于频繁，请稍后重试"),

    /* ===== 服务端错误 ===== */
    INTERNAL_SERVER_ERROR(500, "服务器内部错误"),
    SERVICE_UNAVAILABLE(503, "服务不可用"),
    GATEWAY_TIMEOUT(504, "网关超时"),

    /* ===== 业务错误 6xxx ===== */
    BIZ_ERROR(6000, "业务处理失败"),
    DATA_NOT_EXIST(6001, "数据不存在"),
    DATA_ALREADY_EXIST(6002, "数据已存在"),
    DATA_VALIDATION_FAILED(6003, "数据校验失败"),
    OPERATION_FAILED(6004, "操作失败"),

    /* ===== 用户/认证 61xx ===== */
    USER_NOT_FOUND(6100, "用户不存在"),
    USER_DISABLED(6101, "用户已被禁用"),
    USER_PASSWORD_ERROR(6102, "用户名或密码错误"),
    TOKEN_EXPIRED(6103, "Token 已过期"),
    TOKEN_INVALID(6104, "Token 无效"),
    TOKEN_MISSING(6105, "缺少认证 Token"),
    REFRESH_TOKEN_EXPIRED(6106, "刷新 Token 已过期"),

    /* ===== 订单 62xx ===== */
    ORDER_NOT_FOUND(6200, "订单不存在"),
    ORDER_STATUS_ERROR(6201, "订单状态异常"),
    ORDER_CANCEL_FAILED(6202, "订单取消失败"),

    /* ===== 商品 63xx ===== */
    PRODUCT_NOT_FOUND(6300, "商品不存在"),
    PRODUCT_OFF_SHELF(6301, "商品已下架"),
    STOCK_INSUFFICIENT(6302, "库存不足"),

    /* ===== 支付/结算 64xx ===== */
    PAYMENT_FAILED(6400, "支付失败"),
    PAYMENT_TIMEOUT(6401, "支付超时"),
    BALANCE_INSUFFICIENT(6402, "余额不足"),

    /* ===== 第三方服务 65xx ===== */
    THIRD_PARTY_ERROR(6500, "第三方服务异常"),
    SMS_SEND_FAILED(6501, "短信发送失败"),
    EMAIL_SEND_FAILED(6502, "邮件发送失败");

    private final int code;
    private final String message;

    /**
     * 根据 code 查找枚举（找不到返回 BIZ_ERROR）
     */
    public static ResultCode of(int code) {
        for (ResultCode rc : values()) {
            if (rc.code == code) {
                return rc;
            }
        }
        return BIZ_ERROR;
    }

    public boolean isSuccess() {
        return this == SUCCESS;
    }
}
