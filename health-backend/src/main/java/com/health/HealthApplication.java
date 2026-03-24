package com.health;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * 健康检查系统 - 启动类
 */
@SpringBootApplication
@MapperScan("com.health.mapper")
@EnableScheduling
public class HealthApplication {

    public static void main(String[] args) {
        SpringApplication.run(HealthApplication.class, args);
        System.out.println("==========================================");
        System.out.println("  健康检查系统 启动成功！");
        System.out.println("  API文档: http://localhost:8080/api/doc.html");
        System.out.println("==========================================");
    }
}
