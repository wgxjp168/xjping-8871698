package com.ilbuy.websocket.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * JWT 配置属性（握手阶段验证使用）
 */
@Data
@Component
@ConfigurationProperties(prefix = "ilbuy.jwt")
public class JwtProperties {

    /** HMAC-SHA256 签名密钥，与 auth-svc 保持一致 */
    private String secret = "ilbuy-platform-jwt-secret-key-2024-must-be-at-least-256-bits";
}
