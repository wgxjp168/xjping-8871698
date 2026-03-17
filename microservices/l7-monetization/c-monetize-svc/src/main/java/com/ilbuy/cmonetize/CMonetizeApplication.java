package com.ilbuy.cmonetize;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class CMonetizeApplication {
    public static void main(String[] args) {
        SpringApplication.run(CMonetizeApplication.class, args);
    }
}
