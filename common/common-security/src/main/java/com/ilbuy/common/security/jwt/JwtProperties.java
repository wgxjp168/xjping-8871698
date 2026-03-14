package com.ilbuy.common.security.jwt;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * JWT配置属性
 *
 * <p>在 application.yml 中配置：
 * <pre>
 * ilbuy:
 *   security:
 *     jwt:
 *       secret: your-256-bit-secret-key-here-must-be-long-enough
 *       expiration: 7200000        # 2小时（毫秒）
 *       refresh-expiration: 604800000  # 7天（毫秒）
 *       token-header: Authorization
 *       token-prefix: "Bearer "
 * </pre>
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@Data
@ConfigurationProperties(prefix = "ilbuy.security.jwt")
public class JwtProperties {

    /**
     * JWT签名密钥（至少32个字符）
     * 生产环境通过Vault注入，禁止硬编码
     */
    private String secret = "ilbuy-default-secret-key-must-be-at-least-32-chars";

    /**
     * Access Token 有效期（毫秒），默认2小时
     */
    private long expiration = 7_200_000L;

    /**
     * Refresh Token 有效期（毫秒），默认7天
     */
    private long refreshExpiration = 604_800_000L;

    /**
     * Token请求头名称
     */
    private String tokenHeader = "Authorization";

    /**
     * Token前缀
     */
    private String tokenPrefix = "Bearer ";

    /**
     * 是否启用Token黑名单（登出后Token立即失效）
     */
    private boolean enableBlacklist = true;
}
