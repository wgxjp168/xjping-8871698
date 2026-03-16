package com.ilbuy.reportgen.mq;

import com.ilbuy.reportgen.model.dto.ReportGenerateEvent;
import com.ilbuy.reportgen.service.ReportGeneratorService;
import com.rabbitmq.client.Channel;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.amqp.support.AmqpHeaders;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.stereotype.Component;

import java.io.IOException;

/**
 * Consumes report generation requests from L5 REPORT_SVC.
 * Manually ACKs/NACKs for reliable processing.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class ReportGenerateConsumer {

    private final ReportGeneratorService generatorService;

    @RabbitListener(queues = "${rabbitmq.queue.report-generate-request}", ackMode = "MANUAL")
    public void consumeGenerateRequest(ReportGenerateEvent event,
                                       Channel channel,
                                       @Header(AmqpHeaders.DELIVERY_TAG) long deliveryTag) throws IOException {
        log.info("[MQ Consumer] Received generate request: l5ReportNo={}, clientType={}",
                event.getL5ReportNo(), event.getClientType());
        try {
            generatorService.processGenerateEvent(event);
            channel.basicAck(deliveryTag, false);
            log.debug("[MQ Consumer] ACK deliveryTag={}", deliveryTag);
        } catch (Exception e) {
            log.error("[MQ Consumer] Failed processing l5ReportNo={}: {}", event.getL5ReportNo(), e.getMessage());
            // NACK with requeue=false → goes to DLQ after max-retries
            channel.basicNack(deliveryTag, false, false);
        }
    }
}
