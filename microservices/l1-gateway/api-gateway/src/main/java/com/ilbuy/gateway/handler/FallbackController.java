package com.ilbuy.gateway.handler;

import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

import java.util.Map;

/**
 * 熔断降级 Fallback 控制器
 *
 * <p>当下游服务熔断时，返回统一的降级响应。
 *
 * @author ILbuy Team
 */
@Slf4j
@RestController
@RequestMapping("/fallback")
public class FallbackController {

    @RequestMapping("/auth")
    public Mono<ResponseEntity<Map<String, Object>>> authFallback() {
        log.warn("[熔断降级] auth-svc 不可用");
        return Mono.just(ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(
            fallbackBody(503, "认证服务暂时不可用，请稍后重试")));
    }

    @RequestMapping("/input")
    public Mono<ResponseEntity<Map<String, Object>>> inputFallback() {
        log.warn("[熔断降级] multimodal-input-svc 不可用");
        return Mono.just(ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(
            fallbackBody(503, "输入服务暂时不可用，请稍后重试")));
    }

    @RequestMapping("/generic")
    public Mono<ResponseEntity<Map<String, Object>>> genericFallback() {
        log.warn("[熔断降级] 下游服务不可用");
        return Mono.just(ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(
            fallbackBody(503, "服务暂时不可用，请稍后重试")));
    }

    private Map<String, Object> fallbackBody(int code, String message) {
        return Map.of(
            "code", code,
            "message", message,
            "timestamp", System.currentTimeMillis()
        );
    }
}
