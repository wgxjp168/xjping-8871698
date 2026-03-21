package com.ilbuy.common.security.jwt;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * JWT 配置属性
 *
 * <p>由 {@link com.ilbuy.common.security.config.SecurityAutoConfiguration}
 * 通过 {@code @EnableConfigurationProperties} 注册，消费方无需额外配置。</p>
 *
 * <pre>application.yml:
 * ilbuy:
 *   security:
 *     jwt:
 *       secret: your-256-bit-secret-key-base64-encoded-here
 *       access-token-expire: 7200      # 秒，默认2小时
 *       refresh-token-expire: 604800   # 秒，默认7天
 *       issuer: ilbuy-platform
 * </pre>
 */
@Data
@ConfigurationProperties(prefix = "ilbuy.security.jwt")
public class JwtProperties {

    /**
     * JWT 签名密钥（Base64 编码，至少 256 bit）
     */
    private String secret;

    /**
     * Access Token 过期时间（秒），默认 2 小时
     */
    private long accessTokenExpire = 7_200L;

    /**
     * Refresh Token 过期时间（秒），默认 7 天
     */
    private long refreshTokenExpire = 604_800L;

    /**
     * JWT 签发者
     */
    private String issuer = "ilbuy-platform";

    /**
     * Token 黑名单 Redis Key 前缀
     */
    private String blacklistKeyPrefix = "ilbuy:token:blacklist:";
}
