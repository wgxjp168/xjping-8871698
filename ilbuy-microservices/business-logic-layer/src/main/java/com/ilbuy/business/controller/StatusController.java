package com.ilbuy.business.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.Map;

@RestController
public class StatusController {

    @GetMapping("/api/status")
    public ResponseEntity<Map<String, Object>> status() {
        return ResponseEntity.ok(Map.of(
                "service", "ILbuy Business Logic Layer",
                "status", "running",
                "version", "1.0.0-SNAPSHOT",
                "modules", Map.of(
                        "users", "/api/users",
                        "products", "/api/products",
                        "orders", "/api/orders",
                        "cart", "/api/cart"
                ),
                "timestamp", LocalDateTime.now().toString()
        ));
    }
}
