package com.hd.dr;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = {"com.hd"})
@MapperScan("com.hd.dr.mapper")
public class DrApplication {
    public static void main(String[] args) {
        SpringApplication.run(DrApplication.class, args);
    }
}
