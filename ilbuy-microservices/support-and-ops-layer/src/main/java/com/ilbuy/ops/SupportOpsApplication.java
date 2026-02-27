package com.ilbuy.ops;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class SupportOpsApplication {

    public static void main(String[] args) {
        SpringApplication.run(SupportOpsApplication.class, args);
    }
}
