package com.ilbuy.ops.controller;

import com.ilbuy.ops.service.HealthAggregator;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.Map;

@RestController
@RequestMapping("/api/ops")
public class OpsController {

    private final HealthAggregator healthAggregator;

    public OpsController(HealthAggregator healthAggregator) {
        this.healthAggregator = healthAggregator;
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> status() {
        return ResponseEntity.ok(Map.of(
                "service", "ILbuy Support & Ops Layer",
                "status", "running",
                "version", "1.0.0-SNAPSHOT",
                "capabilities", Map.of(
                        "healthAggregation", "聚合所有微服务健康状态",
                        "dashboard", "运维仪表盘",
                        "serviceRegistry", "服务注册信息"
                ),
                "timestamp", LocalDateTime.now().toString()
        ));
    }

    @GetMapping("/health/all")
    public ResponseEntity<Map<String, HealthAggregator.ServiceHealth>> allHealth() {
        return ResponseEntity.ok(healthAggregator.getAllHealth());
    }

    @GetMapping("/dashboard")
    public ResponseEntity<Map<String, Object>> dashboard() {
        var health = healthAggregator.getAllHealth();
        long upCount = health.values().stream().filter(h -> "UP".equals(h.status())).count();
        long downCount = health.values().stream().filter(h -> "DOWN".equals(h.status())).count();
        return ResponseEntity.ok(Map.of(
                "platform", "ILbuy (我来购) AI智能体微服务平台",
                "totalServices", health.size(),
                "servicesUp", upCount,
                "servicesDown", downCount,
                "overallStatus", downCount == 0 && upCount > 0 ? "HEALTHY" : upCount == 0 ? "INITIALIZING" : "DEGRADED",
                "services", health,
                "timestamp", LocalDateTime.now().toString()
        ));
    }

    @GetMapping("/services")
    public ResponseEntity<Map<String, Object>> serviceRegistry() {
        return ResponseEntity.ok(Map.of(
                "services", Map.of(
                        "access-layer", Map.of("port", 8080, "type", "API Gateway", "tech", "Spring Cloud Gateway"),
                        "ai-decision-hub", Map.of("port", 8081, "type", "AI Service", "tech", "Spring Boot Web"),
                        "business-logic", Map.of("port", 8082, "type", "Business Service", "tech", "Spring Boot Web"),
                        "data-layer", Map.of("port", 8083, "type", "Data Service", "tech", "Spring Data JPA + H2"),
                        "support-ops", Map.of("port", 8084, "type", "Ops Service", "tech", "Spring Boot Web")
                )
        ));
    }
}
