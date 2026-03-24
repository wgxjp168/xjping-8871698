package com.health.physical.auth;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * 权限服务启动类
 * 端口：9005
 * 职责：医生账号管理、项目权限校验、县域账号同步
 */
@SpringBootApplication(scanBasePackages = {"com.health.physical.auth", "com.health.physical.common"})
@MapperScan("com.health.physical.auth.mapper")
@EnableScheduling
public class AuthApplication {

    public static void main(String[] args) {
        SpringApplication.run(AuthApplication.class, args);
    }
}
