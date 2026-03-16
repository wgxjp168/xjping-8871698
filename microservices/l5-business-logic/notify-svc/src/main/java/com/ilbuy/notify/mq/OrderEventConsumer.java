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
 * Consumes order status change events from the order.events queue.
 * When an order.status.changed event arrives, it builds and dispatches
 * an ORDER_STATUS notification to the affected user.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class OrderEventConsumer {

    private final NotificationService notificationService;

    @RabbitListener(queues = "${rabbitmq.order.queue}")
    public void handleOrderEvent(Map<String, Object> event) {
        String eventType = (String) event.get("eventType");
        log.info("Received order event: {}", eventType);

        if (!"order.status.changed".equals(eventType)) {
            log.debug("Ignoring order event type: {}", eventType);
            return;
        }

        Object userIdObj = event.get("userId");
        if (userIdObj == null) {
            log.warn("Order event missing userId, skipping");
            return;
        }

        Long userId = userIdObj instanceof Number
            ? ((Number) userIdObj).longValue()
            : Long.parseLong(userIdObj.toString());

        String orderId = event.getOrDefault("orderId", "").toString();
        String status  = event.getOrDefault("status", "").toString();

        Map<String, String> variables = new HashMap<>();
        variables.put("orderId", orderId);
        variables.put("status", status);

        // Use SMS as the default channel for order status changes
        try {
            notificationService.sendInternal(userId, NotificationChannel.SMS, NotificationType.ORDER_STATUS, variables);
            log.info("Order status notification sent to userId={} for orderId={}, status={}", userId, orderId, status);
        } catch (Exception e) {
            log.error("Failed to send order status notification to userId={}: {}", userId, e.getMessage());
        }
    }
}
