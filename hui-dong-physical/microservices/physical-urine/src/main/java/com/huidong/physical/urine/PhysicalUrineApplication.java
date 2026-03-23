package com.huidong.physical.urine;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

/**
 * 下乡尿机专用服务启动类
 * 端口：9010
 * 职责：仅处理下乡手提电脑通过4G/5G上传的尿常规数据
 *       支持弱网断点续传、去重幂等
 */
@SpringBootApplication(scanBasePackages = {"com.huidong.physical.urine", "com.huidong.physical.common"})
@EnableDiscoveryClient
public class PhysicalUrineApplication {

    public static void main(String[] args) {
        SpringApplication.run(PhysicalUrineApplication.class, args);
    }
}
