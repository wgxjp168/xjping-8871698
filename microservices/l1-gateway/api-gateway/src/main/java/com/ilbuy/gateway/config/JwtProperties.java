package com.ilbuy.gateway.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * JWT 配置属性（与 auth-svc 保持一致）
 */
@Data
@Component
@ConfigurationProperties(prefix = "ilbuy.jwt")
public class JwtProperties {

    /** HMAC-SHA256 签名密钥（Base64编码，生产环境从配置中心读取）*/
    private String secret = "ilbuy-platform-jwt-secret-key-2024-must-be-at-least-256-bits";

    /** 访问令牌有效期（秒），默认2小时 */
    private long accessTokenTtl = 7200;

    /** Token 黑名单 Redis Key 前缀 */
    private String blacklistKeyPrefix = "jwt:blacklist:";
}
