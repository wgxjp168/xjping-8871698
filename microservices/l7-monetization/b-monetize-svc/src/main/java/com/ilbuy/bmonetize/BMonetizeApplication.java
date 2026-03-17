package com.ilbuy.bmonetize;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class BMonetizeApplication {
    public static void main(String[] args) {
        SpringApplication.run(BMonetizeApplication.class, args);
    }
}
