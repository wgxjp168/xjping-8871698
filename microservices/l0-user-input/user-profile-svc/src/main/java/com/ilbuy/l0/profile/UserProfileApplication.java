package com.ilbuy.l0.profile;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.cloud.openfeign.EnableFeignClients;

/**
 * L0 用户画像服务启动类
 *
 * <p>职责：管理用户的历史购物偏好、预算区间、场景标签和行为数据，
 * 为 L0 多模态输入解析提供用户画像上下文，同时供 L1/L2 决策引擎消费。
 *
 * <p>数据来源：
 * <ul>
 *   <li>MySQL（持久化画像）</li>
 *   <li>Redis（热点画像缓存，TTL 30min）</li>
 * </ul>
 *
 * <p>端口：8001
 *
 * @author ILbuy Team
 */
@SpringBootApplication(scanBasePackages = {
        "com.ilbuy.l0.profile",
        "com.ilbuy.common"
})
@EnableDiscoveryClient
@EnableFeignClients(basePackages = "com.ilbuy.l0.profile.client")
@MapperScan("com.ilbuy.l0.profile.mapper")
@EnableCaching
public class UserProfileApplication {

    public static void main(String[] args) {
        SpringApplication.run(UserProfileApplication.class, args);
    }
}
