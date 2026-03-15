package com.ilbuy.l0.input;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.cloud.openfeign.EnableFeignClients;

/**
 * L0 多模态输入适配服务启动类
 *
 * <p>职责：接收终端用户的多种输入形式（文本/图片/链接/语音），
 * 统一解析为标准 {@link com.ilbuy.l0.input.domain.dto.ParsedInput} 对象，
 * 向下传递至 L1 API 网关进入决策流程。
 *
 * <p>端口：8000
 *
 * @author ILbuy Team
 */
@SpringBootApplication(scanBasePackages = {
        "com.ilbuy.l0.input",
        "com.ilbuy.common"
})
@EnableDiscoveryClient
@EnableFeignClients(basePackages = "com.ilbuy.l0.input.client")
public class MultimodalInputApplication {

    public static void main(String[] args) {
        SpringApplication.run(MultimodalInputApplication.class, args);
    }
}
