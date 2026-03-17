package com.ilbuy.datamonetize;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class DataMonetizeApplication {
    public static void main(String[] args) {
        SpringApplication.run(DataMonetizeApplication.class, args);
    }
}
