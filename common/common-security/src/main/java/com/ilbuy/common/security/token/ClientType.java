package com.ilbuy.common.security.token;

import lombok.Getter;
import lombok.RequiredArgsConstructor;

/**
 * 客户端类型枚举（多端鉴权）
 *
 * <p>不同端对应不同的 Token 有效期策略：</p>
 * <ul>
 *   <li>MOBILE  — 移动端：Access 7天（长期持有，用户体验优先）</li>
 *   <li>WEB     — PC/浏览器：Access 2小时（安全优先，会话较短）</li>
 *   <li>ADMIN   — 管理后台：Access 30分钟（最严格，需频繁验证）</li>
 *   <li>OPEN    — 开放平台/第三方：Access 1小时（API Key场景）</li>
 *   <li>DEVICE  — IoT/设备端：Access 30天（设备长时离线）</li>
 * </ul>
 *
 * <pre>{@code
 * // 按客户端类型生成 Token
 * String token = jwtTokenProvider.generateAccessToken(loginUser, ClientType.MOBILE);
 *
 * // 解析时获取客户端类型
 * ClientType type = jwtTokenProvider.getClientType(token);
 * }</pre>
 */
@Getter
@RequiredArgsConstructor
public enum ClientType {

    /** 移动端（Android / iOS / 小程序） */
    MOBILE("mobile", 604_800L, 2_592_000L),      // Access 7d, Refresh 30d

    /** Web 浏览器端 */
    WEB("web", 7_200L, 604_800L),                 // Access 2h, Refresh 7d

    /** 管理后台 */
    ADMIN("admin", 1_800L, 86_400L),              // Access 30min, Refresh 1d

    /** 开放平台 / 第三方 API */
    OPEN("open", 3_600L, 2_592_000L),             // Access 1h, Refresh 30d

    /** IoT / 设备端 */
    DEVICE("device", 2_592_000L, 31_536_000L);    // Access 30d, Refresh 1y

    /** 客户端标识（存入 JWT claims） */
    private final String code;

    /** Access Token 过期时间（秒） */
    private final long accessTokenExpire;

    /** Refresh Token 过期时间（秒） */
    private final long refreshTokenExpire;

    /**
     * 根据 code 解析枚举（找不到返回 WEB 作为默认）
     */
    public static ClientType of(String code) {
        if (code == null) return WEB;
        for (ClientType ct : values()) {
            if (ct.code.equalsIgnoreCase(code)) {
                return ct;
            }
        }
        return WEB;
    }
}
