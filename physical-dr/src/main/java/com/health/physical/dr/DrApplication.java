package com.health.physical.dr;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * DR服务启动类
 * 端口：9011
 * 职责：DR条码解析、DR检查记录入库、DR数据同步县域公卫
 */
@SpringBootApplication(scanBasePackages = {"com.health.physical.dr", "com.health.physical.common"})
@MapperScan("com.health.physical.dr.mapper")
@EnableAsync
@EnableScheduling
public class DrApplication {

    public static void main(String[] args) {
        SpringApplication.run(DrApplication.class, args);
    }
}
