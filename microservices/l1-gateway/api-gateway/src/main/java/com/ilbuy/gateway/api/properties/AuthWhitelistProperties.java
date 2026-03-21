package com.ilbuy.gateway.api.properties;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * 鉴权白名单配置
 *
 * <pre>application.yml:
 * ilbuy:
 *   gateway:
 *     auth:
 *       whitelist:
 *         - /api/v1/auth/**
 *         - /api/v1/public/**
 *         - /actuator/health
 * </pre>
 */
@Data
@Component
@ConfigurationProperties(prefix = "ilbuy.gateway.auth")
public class AuthWhitelistProperties {

    /**
     * 不需要 JWT 鉴权的路径前缀列表（AntPath 匹配）
     */
    private List<String> whitelist = List.of(
            "/api/v1/auth/**",
            "/api/v1/public/**",
            "/actuator/health",
            "/actuator/info",
            "/v3/api-docs/**",
            "/swagger-ui/**",
            "/swagger-ui.html"
    );
}
