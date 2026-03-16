package com.ilbuy.order.mq;

import com.ilbuy.order.model.entity.Order;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * 订单事件异步发布到 RabbitMQ，供下游服务（通知/库存/BI）消费
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class OrderEventPublisher {

    private final RabbitTemplate rabbitTemplate;

    @Value("${rabbitmq.order.exchange:order.topic}")
    private String exchange;

    @Async
    public void publishOrderCreated(Order order) {
        publish("order.created", order);
    }

    @Async
    public void publishOrderPaid(Order order) {
        publish("order.paid", order);
    }

    @Async
    public void publishOrderCancelled(Order order) {
        publish("order.cancelled", order);
    }

    @Async
    public void publishOrderDelivered(Order order) {
        publish("order.delivered", order);
    }

    private void publish(String routingKey, Order order) {
        try {
            Map<String, Object> payload = Map.of(
                "orderId",  order.getId(),
                "orderNo",  order.getOrderNo(),
                "userId",   order.getUserId(),
                "status",   order.getStatus().name(),
                "amount",   order.getFinalAmount()
            );
            rabbitTemplate.convertAndSend(exchange, routingKey, payload);
            log.debug("Published {} for order {}", routingKey, order.getOrderNo());
        } catch (Exception e) {
            log.error("Failed to publish {} for order {}: {}", routingKey, order.getOrderNo(), e.getMessage());
        }
    }
}
