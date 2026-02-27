package com.ilbuy.ops.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class HealthAggregator {

    private static final Logger log = LoggerFactory.getLogger(HealthAggregator.class);
    private final WebClient webClient = WebClient.create();
    private final Map<String, ServiceHealth> healthMap = new ConcurrentHashMap<>();

    private static final Map<String, String> SERVICES = Map.of(
            "access-layer", "http://access-layer:8080/actuator/health",
            "ai-decision-hub", "http://ai-decision-hub:8081/actuator/health",
            "business-logic", "http://business-logic:8082/actuator/health",
            "data-layer", "http://data-layer:8083/actuator/health"
    );

    @Scheduled(fixedRate = 30000, initialDelay = 5000)
    public void checkAllServices() {
        SERVICES.forEach((name, url) -> checkService(name, url));
    }

    private void checkService(String name, String url) {
        try {
            webClient.get().uri(url)
                    .retrieve()
                    .bodyToMono(String.class)
                    .subscribe(
                            body -> {
                                healthMap.put(name, new ServiceHealth(name, "UP", LocalDateTime.now(), null));
                                log.debug("服务 {} 健康检查通过", name);
                            },
                            error -> {
                                healthMap.put(name, new ServiceHealth(name, "DOWN", LocalDateTime.now(), error.getMessage()));
                                log.warn("服务 {} 健康检查失败: {}", name, error.getMessage());
                            }
                    );
        } catch (Exception e) {
            healthMap.put(name, new ServiceHealth(name, "UNKNOWN", LocalDateTime.now(), e.getMessage()));
        }
    }

    public Map<String, ServiceHealth> getAllHealth() {
        return Map.copyOf(healthMap);
    }

    public record ServiceHealth(String service, String status, LocalDateTime lastCheck, String error) {}
}
