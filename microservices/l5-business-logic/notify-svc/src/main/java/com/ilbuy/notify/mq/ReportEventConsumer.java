package com.ilbuy.notify.mq;

import com.ilbuy.notify.model.enums.NotificationChannel;
import com.ilbuy.notify.model.enums.NotificationType;
import com.ilbuy.notify.service.NotificationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

/**
 * Consumes report.ready events from the report.ready queue.
 * When a report is ready, it notifies the owner via EMAIL.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class ReportEventConsumer {

    private final NotificationService notificationService;

    @RabbitListener(queues = "${rabbitmq.report.queue}")
    public void handleReportReadyEvent(Map<String, Object> event) {
        String eventType = (String) event.get("eventType");
        log.info("Received report event: {}", eventType);

        Object userIdObj = event.get("userId");
        if (userIdObj == null) {
            log.warn("Report event missing userId, skipping");
            return;
        }

        Long userId = userIdObj instanceof Number
            ? ((Number) userIdObj).longValue()
            : Long.parseLong(userIdObj.toString());

        String reportNo = event.getOrDefault("reportNo", "").toString();
        String title    = event.getOrDefault("title", "").toString();

        Map<String, String> variables = new HashMap<>();
        variables.put("reportNo", reportNo);
        variables.put("title", title);

        try {
            notificationService.sendInternal(userId, NotificationChannel.EMAIL, NotificationType.REPORT_READY, variables);
            log.info("Report ready notification sent to userId={} for reportNo={}", userId, reportNo);
        } catch (Exception e) {
            log.error("Failed to send report ready notification to userId={}: {}", userId, e.getMessage());
        }
    }
}
