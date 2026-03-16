package com.ilbuy.price;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class PriceSvcApplication {

    public static void main(String[] args) {
        SpringApplication.run(PriceSvcApplication.class, args);
    }
}
