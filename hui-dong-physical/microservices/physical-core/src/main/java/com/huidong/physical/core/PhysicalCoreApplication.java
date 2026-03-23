package com.huidong.physical.core;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * 核心业务服务启动类
 * 端口：9001
 * 职责：居民信息、体检单、标本管理、质控、业务核心
 */
@SpringBootApplication(scanBasePackages = {"com.huidong.physical.core", "com.huidong.physical.common"})
@EnableDiscoveryClient
@EnableScheduling
@MapperScan("com.huidong.physical.core.mapper")
public class PhysicalCoreApplication {

    public static void main(String[] args) {
        SpringApplication.run(PhysicalCoreApplication.class, args);
    }
}
