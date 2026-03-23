package com.huidong.physical.sync;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * 数据同步上报服务启动类
 * 端口：9004
 * 职责：将体检数据统一上报惠东县县域智慧公卫系统
 *       支持失败重试、对账、日志审计
 */
@SpringBootApplication(scanBasePackages = {"com.huidong.physical.sync", "com.huidong.physical.common"})
@EnableDiscoveryClient
@EnableScheduling
@MapperScan("com.huidong.physical.sync.mapper")
public class PhysicalSyncApplication {

    public static void main(String[] args) {
        SpringApplication.run(PhysicalSyncApplication.class, args);
    }
}
