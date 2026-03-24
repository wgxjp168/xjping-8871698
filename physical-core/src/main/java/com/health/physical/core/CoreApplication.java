package com.health.physical.core;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 核心业务服务启动类
 * 端口：9001
 * 职责：体检记录管理、居民信息、检验结果汇聚
 */
@SpringBootApplication(scanBasePackages = {"com.health.physical.core", "com.health.physical.common"})
@MapperScan("com.health.physical.core.mapper")
public class CoreApplication {

    public static void main(String[] args) {
        SpringApplication.run(CoreApplication.class, args);
    }
}
