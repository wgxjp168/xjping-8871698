package com.health.physical.gateway.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

/**
 * 网关配置属性绑定
 * 使用 @ConfigurationProperties 正确绑定 YAML 列表，
 * 替代原来有 BUG 的 @Value("#{'${gateway.white-list}'.split(',')}")
 */
@Data
@Component
@ConfigurationProperties(prefix = "gateway")
public class GatewayProperties {

    /**
     * 鉴权白名单路径（ant 通配符），对应 application.yml 中的 gateway.white-list
     */
    private List<String> whiteList = new ArrayList<>();

    /**
     * JWT Secret（对应 application.yml 中 gateway.jwt-secret）
     * Spring Boot 自动将 kebab-case 转 camelCase
     */
    private String jwtSecret = "physical_health_system_jwt_secret_key_2024_secure_enough";
}
