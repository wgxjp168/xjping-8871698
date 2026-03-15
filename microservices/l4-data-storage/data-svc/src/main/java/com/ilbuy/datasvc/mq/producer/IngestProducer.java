package com.ilbuy.datasvc.mq.producer;

import com.ilbuy.datasvc.model.dto.ProductIngestDTO;
import com.ilbuy.datasvc.mq.config.RabbitMQConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Component;

/**
 * RabbitMQ 生产者 — 发送商品数据到异步处理队列
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class IngestProducer {

    private final RabbitTemplate rabbitTemplate;

    /**
     * 发送到 ES 索引队列（消费者写入 Elasticsearch）
     */
    public void sendToEsQueue(ProductIngestDTO dto) {
        try {
            rabbitTemplate.convertAndSend(
                RabbitMQConfig.EXCHANGE,
                RabbitMQConfig.RK_ES,
                dto
            );
            log.debug("Sent to ES queue: canonicalId={}", dto.getCanonicalId());
        } catch (Exception e) {
            log.error("Failed to send to ES queue canonicalId={}: {}", dto.getCanonicalId(), e.getMessage());
        }
    }

    /**
     * 发送到分析队列（消费者写入 ClickHouse）
     */
    public void sendToAnalyticsQueue(ProductIngestDTO dto) {
        try {
            rabbitTemplate.convertAndSend(
                RabbitMQConfig.EXCHANGE,
                RabbitMQConfig.RK_ANALYTICS,
                dto
            );
            log.debug("Sent to analytics queue: canonicalId={}", dto.getCanonicalId());
        } catch (Exception e) {
            log.error("Failed to send to analytics queue canonicalId={}: {}", dto.getCanonicalId(), e.getMessage());
        }
    }
}
