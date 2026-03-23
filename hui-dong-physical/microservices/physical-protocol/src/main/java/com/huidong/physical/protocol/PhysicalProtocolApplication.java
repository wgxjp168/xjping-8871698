package com.huidong.physical.protocol;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

/**
 * 协议适配服务启动类
 * 端口：9009
 * 职责：生化/血常规/糖化/尿机 HL7协议解析，不写业务逻辑
 */
@SpringBootApplication(scanBasePackages = {"com.huidong.physical.protocol", "com.huidong.physical.common"})
@EnableDiscoveryClient
public class PhysicalProtocolApplication {

    public static void main(String[] args) {
        SpringApplication.run(PhysicalProtocolApplication.class, args);
    }
}
