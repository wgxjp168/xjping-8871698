package com.ilbuy.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

/**
 * ILbuy API 网关启动类
 *
 * <p>负责：统一入口路由、JWT鉴权过滤、B/C端差异化限流、熔断降级、请求审计日志
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@SpringBootApplication
@EnableDiscoveryClient
public class ApiGatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(ApiGatewayApplication.class, args);
    }
}
