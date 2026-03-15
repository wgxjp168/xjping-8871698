package com.ilbuy.datasvc.mq;

import com.ilbuy.datasvc.model.dto.ProductIngestDTO;
import com.ilbuy.datasvc.model.document.ProductDocument;
import com.ilbuy.datasvc.mq.config.RabbitMQConfig;
import com.ilbuy.datasvc.mq.producer.IngestProducer;
import com.ilbuy.datasvc.repository.es.ProductEsRepository;
import com.ilbuy.datasvc.service.AnalyticsService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.amqp.rabbit.core.RabbitTemplate;

import java.math.BigDecimal;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class IngestProducerConsumerTest {

    // ── Producer tests ────────────────────────────────────────────────

    @Mock RabbitTemplate rabbitTemplate;
    @InjectMocks IngestProducer producer;

    @Test
    void sendToEsQueue_callsRabbitTemplate() {
        ProductIngestDTO dto = makeDto("cid-p1");
        producer.sendToEsQueue(dto);
        verify(rabbitTemplate).convertAndSend(
            eq(RabbitMQConfig.EXCHANGE),
            eq(RabbitMQConfig.RK_ES),
            eq(dto)
        );
    }

    @Test
    void sendToAnalyticsQueue_callsRabbitTemplate() {
        ProductIngestDTO dto = makeDto("cid-p2");
        producer.sendToAnalyticsQueue(dto);
        verify(rabbitTemplate).convertAndSend(
            eq(RabbitMQConfig.EXCHANGE),
            eq(RabbitMQConfig.RK_ANALYTICS),
            eq(dto)
        );
    }

    @Test
    void sendToEsQueue_rabbitException_doesNotPropagate() {
        doThrow(new RuntimeException("RabbitMQ down"))
            .when(rabbitTemplate).convertAndSend(anyString(), anyString(), any(Object.class));

        // Should not throw
        producer.sendToEsQueue(makeDto("cid-p3"));
    }

    private ProductIngestDTO makeDto(String canonicalId) {
        ProductIngestDTO dto = new ProductIngestDTO();
        dto.setCanonicalId(canonicalId);
        dto.setPlatform("taobao");
        dto.setProductId("tb_123");
        dto.setTitle("测试商品");
        dto.setPrice(new BigDecimal("199.0"));
        dto.setTotalScore(72.0);
        dto.setGrade("B");
        return dto;
    }
}
