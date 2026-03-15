package com.ilbuy.datasvc.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ilbuy.datasvc.model.dto.IngestRequest;
import com.ilbuy.datasvc.model.dto.IngestResponse;
import com.ilbuy.datasvc.model.dto.ProductIngestDTO;
import com.ilbuy.datasvc.model.entity.Product;
import com.ilbuy.datasvc.mq.producer.IngestProducer;
import com.ilbuy.datasvc.repository.mysql.PriceHistoryRepository;
import com.ilbuy.datasvc.repository.mysql.ProductRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class IngestServiceTest {

    @Mock ProductRepository      productRepository;
    @Mock PriceHistoryRepository priceHistoryRepository;
    @Mock CacheService           cacheService;
    @Mock IngestProducer         ingestProducer;

    @InjectMocks IngestService ingestService;

    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
        // 注入 ObjectMapper（因字段注入被 Mockito 跳过）
        try {
            var field = IngestService.class.getDeclaredField("objectMapper");
            field.setAccessible(true);
            field.set(ingestService, objectMapper);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    @Test
    void ingest_newProduct_savesToMysqlAndQueue() {
        // given
        ProductIngestDTO dto = makeDto("cid-001");
        IngestRequest req = new IngestRequest();
        req.setJobId("job-1");
        req.setSessionId("sess-1");
        req.setProducts(List.of(dto));

        when(productRepository.findByCanonicalId("cid-001")).thenReturn(Optional.empty());
        when(productRepository.save(any())).thenReturn(new Product());
        when(priceHistoryRepository.save(any())).thenReturn(null);

        // when
        IngestResponse resp = ingestService.ingest(req);

        // then
        assertThat(resp.getJobId()).isEqualTo("job-1");
        assertThat(resp.getTotal()).isEqualTo(1);
        assertThat(resp.getSaved()).isEqualTo(1);
        assertThat(resp.getFailed()).isEqualTo(0);
        assertThat(resp.getStatus()).isEqualTo("success");

        verify(productRepository).save(any(Product.class));
        verify(cacheService).cacheProduct(dto);
        verify(ingestProducer).sendToEsQueue(dto);
        verify(ingestProducer).sendToAnalyticsQueue(dto);
    }

    @Test
    void ingest_existingProduct_updatesAndQueues() {
        // given
        ProductIngestDTO dto = makeDto("cid-002");
        IngestRequest req = new IngestRequest();
        req.setJobId("job-2");
        req.setSessionId("sess-2");
        req.setProducts(List.of(dto));

        Product existing = new Product();
        existing.setCanonicalId("cid-002");
        when(productRepository.findByCanonicalId("cid-002")).thenReturn(Optional.of(existing));

        // when
        IngestResponse resp = ingestService.ingest(req);

        // then
        assertThat(resp.getSaved()).isEqualTo(1);
        verify(productRepository).save(existing);   // update path
    }

    @Test
    void ingest_partialFailure_returnsPartialStatus() {
        // given
        ProductIngestDTO good = makeDto("cid-good");
        ProductIngestDTO bad  = makeDto("cid-bad");
        IngestRequest req = new IngestRequest();
        req.setJobId("job-3");
        req.setSessionId("sess-3");
        req.setProducts(List.of(good, bad));

        when(productRepository.findByCanonicalId("cid-good")).thenReturn(Optional.empty());
        when(productRepository.findByCanonicalId("cid-bad"))
            .thenThrow(new RuntimeException("DB error"));
        when(productRepository.save(any())).thenReturn(new Product());

        // when
        IngestResponse resp = ingestService.ingest(req);

        // then
        assertThat(resp.getSaved()).isEqualTo(1);
        assertThat(resp.getFailed()).isEqualTo(1);
        assertThat(resp.getStatus()).isEqualTo("partial");
    }

    @Test
    void ingest_emptyList_returnsZeroCounts() {
        IngestRequest req = new IngestRequest();
        req.setJobId("job-empty");
        req.setSessionId("sess-empty");
        req.setProducts(List.of());

        IngestResponse resp = ingestService.ingest(req);

        assertThat(resp.getTotal()).isEqualTo(0);
        assertThat(resp.getSaved()).isEqualTo(0);
        verifyNoInteractions(productRepository);
    }

    // ── helpers ───────────────────────────────────────────────────────

    private ProductIngestDTO makeDto(String canonicalId) {
        ProductIngestDTO dto = new ProductIngestDTO();
        dto.setCanonicalId(canonicalId);
        dto.setPlatform("jd");
        dto.setProductId("jd_123");
        dto.setTitle("测试商品");
        dto.setTitleCleaned("测试商品");
        dto.setPrice(new BigDecimal("299.00"));
        dto.setTotalScore(78.5);
        dto.setGrade("B");
        dto.setInStock(true);
        dto.setSalesCount(1000);
        dto.setReviewCount(500);
        dto.setCrawledAt("2024-01-01T00:00:00Z");
        return dto;
    }
}
