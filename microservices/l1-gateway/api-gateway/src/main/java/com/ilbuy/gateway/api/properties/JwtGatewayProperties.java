package com.ilbuy.gateway.api.properties;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * 网关侧 JWT 本地校验配置
 *
 * <pre>application.yml:
 * ilbuy:
 *   gateway:
 *     jwt:
 *       secret: aWxidXktcGxhdGZvcm0tc2VjcmV0LWtleS0zMmJ5dGVz
 *       issuer: ilbuy-platform
 *       blacklist-key-prefix: ilbuy:token:blacklist:
 * </pre>
 */
@Data
@Component
@ConfigurationProperties(prefix = "ilbuy.gateway.jwt")
public class JwtGatewayProperties {

    /** JWT 签名密钥（Base64 编码，与 auth-service 共享同一密钥） */
    private String secret;

    /** JWT 签发者，与生成时一致 */
    private String issuer = "ilbuy-platform";

    /** Token 黑名单 Redis Key 前缀（与 auth-service 共享同一 Redis） */
    private String blacklistKeyPrefix = "ilbuy:token:blacklist:";

    /** Authorization 请求头名称 */
    private String headerName = "Authorization";

    /** Token 前缀 */
    private String tokenPrefix = "Bearer ";
}
