package com.ilbuy.datasvc.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ilbuy.datasvc.model.dto.ProductIngestDTO;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.data.redis.core.ZSetOperations;

import java.math.BigDecimal;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class CacheServiceTest {

    @Mock StringRedisTemplate redisTemplate;
    @Mock ValueOperations<String, String> valueOps;
    @Mock ZSetOperations<String, String> zsetOps;

    @InjectMocks CacheService cacheService;

    private ObjectMapper objectMapper = new ObjectMapper();

    @BeforeEach
    void setUp() throws Exception {
        var field = CacheService.class.getDeclaredField("objectMapper");
        field.setAccessible(true);
        field.set(cacheService, objectMapper);

        when(redisTemplate.opsForValue()).thenReturn(valueOps);
        when(redisTemplate.opsForZSet()).thenReturn(zsetOps);
    }

    @Test
    void cacheProduct_writesKeyAndZSet() {
        ProductIngestDTO dto = makeDto("cid-001", 89.5);

        cacheService.cacheProduct(dto);

        verify(valueOps).set(eq("product:cid-001"), anyString(), any());
        verify(zsetOps).add(eq("product:platform:jd:hot"), eq("cid-001"), eq(89.5));
    }

    @Test
    void getProductJson_returnsValueWhenPresent() {
        when(valueOps.get("product:cid-001")).thenReturn("{\"canonicalId\":\"cid-001\"}");

        Optional<String> result = cacheService.getProductJson("cid-001");

        assertThat(result).isPresent();
        assertThat(result.get()).contains("cid-001");
    }

    @Test
    void getProductJson_returnsEmptyWhenMissing() {
        when(valueOps.get("product:missing")).thenReturn(null);

        Optional<String> result = cacheService.getProductJson("missing");

        assertThat(result).isEmpty();
    }

    @Test
    void cacheProduct_redisException_doesNotPropagate() {
        when(redisTemplate.opsForValue()).thenThrow(new RuntimeException("Redis down"));

        // Should not throw — Redis failure is best-effort
        cacheService.cacheProduct(makeDto("cid-002", 50.0));
    }

    @Test
    void totalIngestCount_returnsZeroOnNullValue() {
        when(valueOps.get("stats:ingest:count")).thenReturn(null);

        assertThat(cacheService.totalIngestCount()).isEqualTo(0L);
    }

    @Test
    void totalIngestCount_returnsParsedValue() {
        when(valueOps.get("stats:ingest:count")).thenReturn("42");

        assertThat(cacheService.totalIngestCount()).isEqualTo(42L);
    }

    private ProductIngestDTO makeDto(String canonicalId, double score) {
        ProductIngestDTO dto = new ProductIngestDTO();
        dto.setCanonicalId(canonicalId);
        dto.setPlatform("jd");
        dto.setProductId("pid");
        dto.setTitle("商品");
        dto.setPrice(new BigDecimal("99.0"));
        dto.setTotalScore(score);
        return dto;
    }
}
