package com.ilbuy.auth.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * JWT 配置属性
 */
@Data
@Component
@ConfigurationProperties(prefix = "ilbuy.jwt")
public class JwtProperties {

    /** HMAC-SHA256 签名密钥（至少 256 bit）*/
    private String secret = "ilbuy-platform-jwt-secret-key-2024-must-be-at-least-256-bits";

    /** 访问令牌有效期（秒），默认 2 小时 */
    private long accessTokenTtl = 7200;

    /** 刷新令牌有效期（秒），默认 7 天 */
    private long refreshTokenTtl = 604800;

    /** Token 黑名单 Redis Key 前缀 */
    private String blacklistKeyPrefix = "jwt:blacklist:";

    /** RefreshToken Redis Key 前缀 */
    private String refreshKeyPrefix = "jwt:refresh:";
}
