package com.ilbuy.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class MonetizeGatewayApplication {
    public static void main(String[] args) {
        SpringApplication.run(MonetizeGatewayApplication.class, args);
    }
}
