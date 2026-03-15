package com.ilbuy.datasvc.service;

import com.ilbuy.datasvc.model.dto.ProductIngestDTO;
import com.ilbuy.datasvc.repository.clickhouse.ClickHouseRepository;
import com.ilbuy.datasvc.repository.mysql.ProductRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 分析服务 — ClickHouse 写入 + MySQL 聚合统计（供 L5 预留）
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class AnalyticsService {

    private final ClickHouseRepository clickHouseRepository;
    private final ProductRepository    productRepository;

    @Async
    public void writeToClickHouse(ProductIngestDTO dto) {
        clickHouseRepository.insertEvent(dto);
    }

    @Async
    public void batchWriteToClickHouse(List<ProductIngestDTO> dtos) {
        log.debug("ClickHouse batch write: {} records", dtos.size());
        clickHouseRepository.batchInsertEvents(dtos);
    }

    public Map<String, Object> getPlatformStats() {
        Map<String, Object> result = new LinkedHashMap<>();
        // MySQL 聚合（实时）
        List<Object[]> rows = productRepository.countGroupByPlatform();
        Map<String, Long> mysqlCounts = rows.stream()
            .collect(Collectors.toMap(
                r -> (String) r[0],
                r -> (Long)   r[1]
            ));
        result.put("mysql_platform_counts", mysqlCounts);

        // ClickHouse 分析（24h）
        try {
            result.put("clickhouse_24h_stats", clickHouseRepository.queryPlatformStats());
        } catch (Exception e) {
            log.warn("ClickHouse stats query failed: {}", e.getMessage());
            result.put("clickhouse_24h_stats", List.of());
        }
        return result;
    }

    public List<Map<String, Object>> getTopBrands(String platform) {
        try {
            return clickHouseRepository.queryTopBrands(platform, 20);
        } catch (Exception e) {
            log.warn("ClickHouse top-brands query failed: {}", e.getMessage());
            return List.of();
        }
    }
}
