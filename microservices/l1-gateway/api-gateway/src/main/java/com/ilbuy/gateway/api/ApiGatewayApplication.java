package com.ilbuy.gateway.api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

/**
 * L1 API 网关启动类
 *
 * <p>架构职责：
 * <ul>
 *   <li>系统唯一南北向流量入口（Kong 之后的第一道 Java 处理节点）</li>
 *   <li>JWT Token 本地校验（避免每次调用 auth-service，降低延迟）</li>
 *   <li>基于 Redis 滑动窗口限流（C端100/min/用户，B端1000/min/IP）</li>
 *   <li>Sentinel 熔断降级（下游响应慢或失败时快速返回）</li>
 *   <li>全链路 TraceID 注入（MDC + 请求头双写，对接 ELK）</li>
 *   <li>请求审计日志（TraceID/UID/路径/耗时/状态码 → ELK）</li>
 * </ul>
 * </p>
 */
@SpringBootApplication
@EnableDiscoveryClient
public class ApiGatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(ApiGatewayApplication.class, args);
    }
}
