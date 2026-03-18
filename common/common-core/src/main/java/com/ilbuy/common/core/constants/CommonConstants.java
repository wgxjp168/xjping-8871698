package com.ilbuy.common.core.constants;

/**
 * 公共常量定义
 */
public final class CommonConstants {

    private CommonConstants() {}

    // ──────────────────── 请求头 ────────────────────

    /** Authorization 请求头名称 */
    public static final String HEADER_AUTHORIZATION = "Authorization";

    /** Bearer Token 前缀 */
    public static final String TOKEN_PREFIX = "Bearer ";

    /** 链路追踪 ID 请求头 */
    public static final String HEADER_TRACE_ID = "X-Trace-Id";

    /** 当前用户 ID 请求头（网关注入） */
    public static final String HEADER_USER_ID = "X-User-Id";

    /** 当前用户名请求头 */
    public static final String HEADER_USERNAME = "X-Username";

    /** 当前用户角色请求头 */
    public static final String HEADER_USER_ROLES = "X-User-Roles";

    /** 租户 ID 请求头 */
    public static final String HEADER_TENANT_ID = "X-Tenant-Id";

    // ──────────────────── JWT Claims ────────────────────

    public static final String JWT_CLAIM_USER_ID   = "userId";
    public static final String JWT_CLAIM_USERNAME  = "username";
    public static final String JWT_CLAIM_ROLES     = "roles";
    public static final String JWT_CLAIM_TENANT_ID = "tenantId";

    // ──────────────────── 缓存 Key 前缀 ────────────────────

    public static final String CACHE_PREFIX          = "ilbuy:";
    public static final String CACHE_USER_PREFIX     = CACHE_PREFIX + "user:";
    public static final String CACHE_TOKEN_PREFIX    = CACHE_PREFIX + "token:";
    public static final String CACHE_CAPTCHA_PREFIX  = CACHE_PREFIX + "captcha:";
    public static final String CACHE_RATE_LIMIT      = CACHE_PREFIX + "rate:";

    // ──────────────────── 分页默认值 ────────────────────

    public static final int DEFAULT_PAGE_NUM  = 1;
    public static final int DEFAULT_PAGE_SIZE = 20;
    public static final int MAX_PAGE_SIZE     = 500;

    // ──────────────────── 逻辑删除 ────────────────────

    public static final int LOGIC_NOT_DELETED = 0;
    public static final int LOGIC_DELETED     = 1;

    // ──────────────────── 状态 ────────────────────

    public static final int STATUS_ENABLE  = 1;
    public static final int STATUS_DISABLE = 0;

    // ──────────────────── 时间格式 ────────────────────

    public static final String DATETIME_FORMAT = "yyyy-MM-dd HH:mm:ss";
    public static final String DATE_FORMAT     = "yyyy-MM-dd";
    public static final String TIME_FORMAT     = "HH:mm:ss";

    // ──────────────────── 正则 ────────────────────

    public static final String REGEX_MOBILE  = "^1[3-9]\\d{9}$";
    public static final String REGEX_EMAIL   = "^[a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,}$";
    public static final String REGEX_ID_CARD = "^[1-9]\\d{5}(18|19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01])\\d{3}[0-9Xx]$";

    // ──────────────────── 特殊字符 ────────────────────

    public static final String COMMA     = ",";
    public static final String SEMICOLON = ";";
    public static final String COLON     = ":";
    public static final String EMPTY     = "";
    public static final String SLASH     = "/";
}
