package com.ilbuy.shop;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.ilbuy.shop.mapper")
public class ShopScoreApplication {
    public static void main(String[] args) {
        SpringApplication.run(ShopScoreApplication.class, args);
    }
}
