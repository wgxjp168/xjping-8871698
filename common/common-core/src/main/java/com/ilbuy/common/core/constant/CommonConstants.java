package com.ilbuy.common.core.constant;

/**
 * 全局公共常量
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
public final class CommonConstants {

    private CommonConstants() {}

    // ==================== HTTP Header ====================
    /** JWT Token请求头 */
    public static final String HEADER_AUTHORIZATION = "Authorization";
    /** Bearer Token前缀 */
    public static final String TOKEN_PREFIX = "Bearer ";
    /** 用户ID请求头（服务内部传递）*/
    public static final String HEADER_USER_ID = "X-User-Id";
    /** 用户类型请求头 */
    public static final String HEADER_USER_TYPE = "X-User-Type";
    /** 会话ID */
    public static final String HEADER_SESSION_ID = "X-Session-Id";
    /** 追踪ID */
    public static final String HEADER_TRACE_ID = "X-Trace-Id";
    /** 请求来源（web/app/miniprogram）*/
    public static final String HEADER_SOURCE = "X-Source";
    /** 内部服务调用标记 */
    public static final String HEADER_INNER_CALL = "X-Inner-Call";
    /** 内部服务调用密钥 */
    public static final String INNER_CALL_SECRET = "ilbuy-inner-secret-2024";

    // ==================== 缓存Key前缀 ====================
    /** Redis Key前缀 */
    public static final String CACHE_PREFIX = "ilbuy:";
    /** 用户Token缓存前缀 */
    public static final String CACHE_TOKEN_PREFIX = CACHE_PREFIX + "token:";
    /** 用户信息缓存前缀 */
    public static final String CACHE_USER_PREFIX = CACHE_PREFIX + "user:";
    /** 决策会话缓存前缀 */
    public static final String CACHE_SESSION_PREFIX = CACHE_PREFIX + "session:";
    /** 限流Key前缀（B端）*/
    public static final String RATE_LIMIT_B_PREFIX = CACHE_PREFIX + "ratelimit:b:";
    /** 限流Key前缀（C端）*/
    public static final String RATE_LIMIT_C_PREFIX = CACHE_PREFIX + "ratelimit:c:";
    /** 验证码缓存前缀 */
    public static final String CACHE_CAPTCHA_PREFIX = CACHE_PREFIX + "captcha:";

    // ==================== 限流配置 ====================
    /** B端限流：1000次/分钟/IP */
    public static final int RATE_LIMIT_B2B_PER_MIN = 1000;
    /** C端限流：100次/分钟/用户 */
    public static final int RATE_LIMIT_B2C_PER_MIN = 100;

    // ==================== Token相关 ====================
    /** Access Token有效期：2小时（毫秒）*/
    public static final long TOKEN_EXPIRATION_MS = 2 * 60 * 60 * 1000L;
    /** Refresh Token有效期：7天（毫秒）*/
    public static final long REFRESH_TOKEN_EXPIRATION_MS = 7 * 24 * 60 * 60 * 1000L;
    /** 验证码有效期：5分钟（秒）*/
    public static final long CAPTCHA_EXPIRATION_SECONDS = 5 * 60L;

    // ==================== 分页默认值 ====================
    /** 默认页码 */
    public static final int DEFAULT_PAGE_NUM = 1;
    /** 默认每页条数 */
    public static final int DEFAULT_PAGE_SIZE = 10;
    /** 最大每页条数 */
    public static final int MAX_PAGE_SIZE = 100;

    // ==================== 业务相关 ====================
    /** 采购决策会话过期时间：30分钟（秒）*/
    public static final long DECISION_SESSION_EXPIRATION_SECONDS = 30 * 60L;
    /** 报告有效期：30天（秒）*/
    public static final long REPORT_EXPIRATION_SECONDS = 30 * 24 * 60 * 60L;
    /** 免费用户每月决策次数 */
    public static final int FREE_USER_MONTHLY_QUOTA = 3;
    /** AI决策最大超时时间：30秒 */
    public static final int AI_DECISION_TIMEOUT_SECONDS = 30;

    // ==================== 电商平台 ====================
    /** 支持的电商平台列表 */
    public static final String[] SUPPORTED_PLATFORMS =
            {"taobao", "tmall", "jd", "pdd", "1688", "vip", "suning", "douyin"};

    // ==================== 正则表达式 ====================
    /** 手机号正则 */
    public static final String REGEX_PHONE = "^1[3-9]\\d{9}$";
    /** 邮箱正则 */
    public static final String REGEX_EMAIL = "^[a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,}$";
    /** 统一社会信用代码正则 */
    public static final String REGEX_CREDIT_CODE = "^[0-9A-HJ-NP-RT-UW-Y]{18}$";
    /** 密码强度：8-20位，包含字母和数字 */
    public static final String REGEX_PASSWORD = "^(?=.*[A-Za-z])(?=.*\\d)[A-Za-z\\d@$!%*#?&]{8,20}$";
}
