package com.ilbuy.common.core.result;

import lombok.Getter;

/**
 * 全局统一响应状态码
 *
 * <p>编码规则：
 * <ul>
 *   <li>2xx - 成功</li>
 *   <li>4xx - 客户端错误</li>
 *   <li>5xx - 服务端错误</li>
 *   <li>1xxx - 用户模块</li>
 *   <li>2xxx - 采购决策模块</li>
 *   <li>3xxx - 支付模块</li>
 *   <li>4xxx - 报告模块</li>
 *   <li>5xxx - 数据采集模块</li>
 * </ul>
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@Getter
public enum ResultCode {

    // ==================== 通用 ====================
    SUCCESS(200, "操作成功"),
    CREATED(201, "创建成功"),
    NO_CONTENT(204, "无内容"),

    BAD_REQUEST(400, "请求参数错误"),
    UNAUTHORIZED(401, "未认证，请先登录"),
    FORBIDDEN(403, "无操作权限"),
    NOT_FOUND(404, "资源不存在"),
    METHOD_NOT_ALLOWED(405, "请求方法不支持"),
    CONFLICT(409, "数据冲突"),
    TOO_MANY_REQUESTS(429, "请求过于频繁，请稍后重试"),
    INTERNAL_ERROR(500, "系统内部错误"),
    SERVICE_UNAVAILABLE(503, "服务不可用"),

    // ==================== 用户模块 1xxx ====================
    USER_NOT_FOUND(1001, "用户不存在"),
    USER_PASSWORD_ERROR(1002, "用户名或密码错误"),
    USER_DISABLED(1003, "账户已被禁用"),
    USER_ALREADY_EXISTS(1004, "用户名已存在"),
    PHONE_ALREADY_EXISTS(1005, "手机号已被注册"),
    EMAIL_ALREADY_EXISTS(1006, "邮箱已被注册"),
    TOKEN_EXPIRED(1007, "Token已过期，请重新登录"),
    TOKEN_INVALID(1008, "Token无效"),
    REFRESH_TOKEN_EXPIRED(1009, "RefreshToken已过期，请重新登录"),
    CAPTCHA_ERROR(1010, "验证码错误或已过期"),
    MEMBER_EXPIRED(1011, "会员已到期"),
    DECISION_QUOTA_EXCEEDED(1012, "本月免费决策次数已用完"),

    // ==================== 采购决策模块 2xxx ====================
    DECISION_PROCESSING(2000, "AI决策进行中"),
    DECISION_TIMEOUT(2001, "AI决策超时，请重试"),
    DECISION_FAILED(2002, "AI决策失败"),
    PLATFORM_API_ERROR(2003, "电商平台数据获取异常"),
    PRODUCT_NOT_FOUND(2004, "未找到匹配商品，请修改搜索条件"),
    INTENT_PARSE_FAILED(2005, "意图解析失败，请重新描述需求"),
    LLM_CALL_FAILED(2006, "大模型调用失败，请稍后重试"),
    IMAGE_PARSE_FAILED(2007, "图片解析失败，请检查图片格式"),
    LINK_PARSE_FAILED(2008, "链接解析失败，请检查链接是否有效"),

    // ==================== 支付模块 3xxx ====================
    PAYMENT_FAILED(3001, "支付失败"),
    PAYMENT_CANCELLED(3002, "支付已取消"),
    ORDER_NOT_FOUND(3003, "订单不存在"),
    ORDER_ALREADY_PAID(3004, "订单已支付"),
    ORDER_EXPIRED(3005, "订单已过期"),
    REFUND_FAILED(3006, "退款失败"),
    INSUFFICIENT_BALANCE(3007, "账户余额不足"),

    // ==================== 报告模块 4xxx ====================
    REPORT_GENERATE_FAILED(4001, "报告生成失败"),
    REPORT_NOT_FOUND(4002, "报告不存在"),
    REPORT_EXPIRED(4003, "报告已过期"),
    REPORT_FORMAT_NOT_SUPPORTED(4004, "不支持的报告格式"),
    PDF_GENERATE_FAILED(4005, "PDF生成失败"),
    EXCEL_GENERATE_FAILED(4006, "Excel生成失败"),

    // ==================== 数据采集模块 5xxx ====================
    CRAWLER_RATE_LIMIT(5001, "采集频率超限，触发平台限流"),
    PLATFORM_API_UNAVAILABLE(5002, "平台API暂时不可用"),
    DATA_QUALITY_TOO_LOW(5003, "采集数据质量不达标");

    /** 状态码 */
    private final int code;

    /** 状态描述 */
    private final String message;

    ResultCode(int code, String message) {
        this.code = code;
        this.message = message;
    }
}
