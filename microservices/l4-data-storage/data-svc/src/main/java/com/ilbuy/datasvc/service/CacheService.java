package com.ilbuy.datasvc.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ilbuy.datasvc.model.dto.ProductIngestDTO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Optional;

/**
 * Redis 缓存服务
 *
 * Key 设计：
 *   product:{canonicalId}           → 商品 JSON（TTL 1h）
 *   product:platform:{platform}:hot → 平台热门商品 ID Set（TTL 10min）
 *   stats:ingest:count              → 入库计数器（永久）
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class CacheService {

    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper        objectMapper;

    private static final Duration PRODUCT_TTL       = Duration.ofHours(1);
    private static final Duration HOT_LIST_TTL      = Duration.ofMinutes(10);
    private static final String   KEY_PREFIX        = "product:";
    private static final String   HOT_PREFIX        = "product:platform:";
    private static final String   INGEST_COUNT_KEY  = "stats:ingest:count";

    public void cacheProduct(ProductIngestDTO dto) {
        try {
            String key  = KEY_PREFIX + dto.getCanonicalId();
            String json = objectMapper.writeValueAsString(dto);
            redisTemplate.opsForValue().set(key, json, PRODUCT_TTL);

            // 维护平台热榜（ZSet，score = totalScore）
            if (dto.getTotalScore() != null) {
                String zKey = HOT_PREFIX + dto.getPlatform() + ":hot";
                redisTemplate.opsForZSet().add(zKey, dto.getCanonicalId(), dto.getTotalScore());
                redisTemplate.expire(zKey, HOT_LIST_TTL);
                // 保留 Top 500
                redisTemplate.opsForZSet().removeRange(zKey, 0, -501);
            }

            redisTemplate.opsForValue().increment(INGEST_COUNT_KEY);
        } catch (Exception e) {
            log.warn("Redis cache write failed for canonicalId={}: {}", dto.getCanonicalId(), e.getMessage());
        }
    }

    public Optional<String> getProductJson(String canonicalId) {
        try {
            String val = redisTemplate.opsForValue().get(KEY_PREFIX + canonicalId);
            return Optional.ofNullable(val);
        } catch (Exception e) {
            log.warn("Redis get failed for canonicalId={}: {}", canonicalId, e.getMessage());
            return Optional.empty();
        }
    }

    public void evict(String canonicalId) {
        redisTemplate.delete(KEY_PREFIX + canonicalId);
    }

    public Long totalIngestCount() {
        try {
            String val = redisTemplate.opsForValue().get(INGEST_COUNT_KEY);
            return val != null ? Long.parseLong(val) : 0L;
        } catch (Exception e) {
            return 0L;
        }
    }
}
