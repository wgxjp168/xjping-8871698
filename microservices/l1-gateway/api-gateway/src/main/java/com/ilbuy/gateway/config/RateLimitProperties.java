package com.ilbuy.gateway.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * 限流配置属性
 *
 * <p>B端（企业）：1000次/分钟/IP；C端（消费者）：100次/分钟/用户
 */
@Data
@Component
@ConfigurationProperties(prefix = "ilbuy.rate-limit")
public class RateLimitProperties {

    /** B端（BUSINESS）每分钟每IP请求上限 */
    private int businessLimitPerMin = 1000;

    /** C端（CONSUMER）每分钟每用户请求上限 */
    private int consumerLimitPerMin = 100;

    /** 限流计数器 Redis Key 过期时间（秒）*/
    private int windowSeconds = 60;

    /** Redis Key 前缀 */
    private String keyPrefix = "rate:limit:";

    /** 无需鉴权的白名单路径 */
    private String[] whitelistPaths = {
        "/auth/login", "/auth/refresh", "/auth/captcha",
        "/actuator/health", "/actuator/info",
        "/v3/api-docs/**", "/swagger-ui/**"
    };
}
