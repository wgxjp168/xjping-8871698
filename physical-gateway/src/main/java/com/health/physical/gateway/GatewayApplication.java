package com.health.physical.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 统一网关启动类
 * 端口：8888
 * 职责：路由转发、JWT鉴权、限流、CORS
 */
@SpringBootApplication(scanBasePackages = {"com.health.physical.gateway", "com.health.physical.common"})
public class GatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(GatewayApplication.class, args);
    }
}
