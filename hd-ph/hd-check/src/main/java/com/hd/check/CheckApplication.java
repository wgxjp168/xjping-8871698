package com.hd.check;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = {"com.hd"})
@MapperScan("com.hd.check.mapper")
public class CheckApplication {
    public static void main(String[] args) {
        SpringApplication.run(CheckApplication.class, args);
    }
}
