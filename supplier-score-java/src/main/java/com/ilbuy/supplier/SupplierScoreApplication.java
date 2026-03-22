package com.ilbuy.supplier;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.ilbuy.supplier.mapper")
public class SupplierScoreApplication {

    public static void main(String[] args) {
        SpringApplication.run(SupplierScoreApplication.class, args);
    }
}
