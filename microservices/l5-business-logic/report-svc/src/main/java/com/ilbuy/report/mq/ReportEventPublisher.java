package com.ilbuy.report.mq;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.Map;

@Component
@RequiredArgsConstructor
@Slf4j
public class ReportEventPublisher {

    private final RabbitTemplate rabbitTemplate;

    @Value("${rabbitmq.report.exchange}")
    private String exchange;

    @Value("${rabbitmq.report.routing-key}")
    private String routingKey;

    /**
     * Publish a report.generate event to trigger async report generation.
     */
    public void publishReportGenerateEvent(String reportNo, Long userId) {
        Map<String, Object> event = Map.of(
            "reportNo", reportNo,
            "userId", userId,
            "eventType", "report.generate"
        );
        log.info("Publishing report.generate event for reportNo={}", reportNo);
        rabbitTemplate.convertAndSend(exchange, routingKey, event);
    }
}
