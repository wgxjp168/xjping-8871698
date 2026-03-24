package com.health.physical.urine;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 尿机服务启动类
 * 端口：9010
 * 职责：优利特尿机数据接收（手提电脑4G/5G上传）、尿常规结果存储
 */
@SpringBootApplication(scanBasePackages = {"com.health.physical.urine", "com.health.physical.common"})
@MapperScan("com.health.physical.urine.mapper")
public class UrineApplication {

    public static void main(String[] args) {
        SpringApplication.run(UrineApplication.class, args);
    }
}
