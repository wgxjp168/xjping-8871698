package com.ilbuy.datasvc.api;

import com.ilbuy.datasvc.service.AnalyticsService;
import com.ilbuy.datasvc.service.CacheService;
import com.ilbuy.datasvc.repository.mysql.ProductRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * GET /stats — 存储层统计（L5 预留）
 * GET /health — 健康检查
 */
@RestController
@RequiredArgsConstructor
public class StatsController {

    private final AnalyticsService  analyticsService;
    private final CacheService      cacheService;
    private final ProductRepository productRepository;

    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> stats(
            @RequestParam(required = false) String platform) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("total_products",    productRepository.count());
        result.put("total_ingest",      cacheService.totalIngestCount());
        result.put("platform_stats",    analyticsService.getPlatformStats());
        if (platform != null) {
            result.put("top_brands", analyticsService.getTopBrands(platform));
        }
        return ResponseEntity.ok(result);
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> health() {
        Map<String, Object> h = new LinkedHashMap<>();
        h.put("status",  "UP");
        h.put("service", "data-svc");
        h.put("version", "1.0.0");
        h.put("time",    Instant.now().toString());
        return ResponseEntity.ok(h);
    }
}
