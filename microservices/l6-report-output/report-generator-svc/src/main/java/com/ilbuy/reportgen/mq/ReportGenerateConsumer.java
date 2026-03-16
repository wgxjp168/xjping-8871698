package com.ilbuy.reportgen.mq;

import com.ilbuy.reportgen.model.dto.ReportGenerateEvent;
import com.ilbuy.reportgen.model.entity.ReportJob;
import com.ilbuy.reportgen.model.enums.JobStatus;
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
 * Consumes report generation requests from L5 REPORT_SVC via RabbitMQ.
 *
 * Two-step processing to avoid @Async + @Transactional proxy pitfall:
 *   1. createJobRecord()  – synchronous, transactional, returns after DB commit
 *   2. processJobAsync()  – asynchronous, runs in dedicated thread pool
 *
 * The MQ ACK is sent after step 1 completes, ensuring the job record
 * is persisted before the message is acknowledged.  If step 2 fails,
 * the RetryScheduler will pick it up.
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
        log.info("[MQ Consumer] Received: l5ReportNo={}, clientType={}", event.getL5ReportNo(), event.getClientType());
        try {
            // Step 1: Synchronously create/find the job record (idempotent)
            ReportJob job = generatorService.createJobRecord(event);

            if (job.getStatus() == JobStatus.COMPLETED) {
                log.warn("[MQ Consumer] Job already completed for l5ReportNo={}, ACK-ing", event.getL5ReportNo());
                channel.basicAck(deliveryTag, false);
                return;
            }

            // ACK the message NOW – job record is committed, async processing is safe
            channel.basicAck(deliveryTag, false);
            log.debug("[MQ Consumer] ACK deliveryTag={}", deliveryTag);

            // Step 2: Kick off async generation (non-blocking for MQ thread)
            generatorService.processJobAsync(job, event);

        } catch (Exception e) {
            log.error("[MQ Consumer] Failed to create job record for l5ReportNo={}: {}", event.getL5ReportNo(), e.getMessage());
            // NACK → DLQ (do not requeue – retry scheduler handles DB-persisted jobs)
            channel.basicNack(deliveryTag, false, false);
        }
    }
}
