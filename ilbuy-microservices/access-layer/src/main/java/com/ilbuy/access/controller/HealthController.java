package com.ilbuy.access.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

import java.time.LocalDateTime;
import java.util.Map;

@RestController
public class HealthController {

    @GetMapping("/")
    public Mono<ResponseEntity<Map<String, Object>>> index() {
        return Mono.just(ResponseEntity.ok(Map.of(
                "service", "ILbuy Access Layer (API Gateway)",
                "status", "running",
                "timestamp", LocalDateTime.now().toString(),
                "version", "1.0.0-SNAPSHOT"
        )));
    }

    @GetMapping("/health")
    public Mono<ResponseEntity<Map<String, String>>> health() {
        return Mono.just(ResponseEntity.ok(Map.of(
                "status", "UP",
                "service", "access-layer"
        )));
    }
}
