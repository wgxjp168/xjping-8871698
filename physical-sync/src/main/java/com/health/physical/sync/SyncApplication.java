package com.health.physical.sync;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.web.client.RestTemplate;

/**
 * 同步服务启动类
 * 端口：9004
 * 职责：体检数据批量同步至县域公卫系统
 */
@SpringBootApplication(scanBasePackages = {"com.health.physical.sync", "com.health.physical.common"})
@MapperScan("com.health.physical.sync.mapper")
public class SyncApplication {

    public static void main(String[] args) {
        SpringApplication.run(SyncApplication.class, args);
    }

    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
}
