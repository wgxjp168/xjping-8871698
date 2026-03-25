package com.hd.resident;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.hd.resident.mapper")
public class ResidentApplication {
    public static void main(String[] args) {
        SpringApplication.run(ResidentApplication.class, args);
    }
}
