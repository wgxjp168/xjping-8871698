package com.ilbuy.format;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

@SpringBootApplication
@EnableAsync
public class FormatOutputApplication {
    public static void main(String[] args) {
        SpringApplication.run(FormatOutputApplication.class, args);
    }
}
