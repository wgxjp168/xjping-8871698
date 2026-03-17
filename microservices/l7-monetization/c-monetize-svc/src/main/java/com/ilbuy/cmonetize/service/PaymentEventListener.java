package com.ilbuy.cmonetize.service;

import com.ilbuy.cmonetize.config.RabbitConfig;
import com.ilbuy.cmonetize.domain.CMonetizeOrder;
import com.ilbuy.cmonetize.repository.CMonetizeOrderRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Service;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class PaymentEventListener {

    private final CMonetizeService cMonetizeService;
    private final SubscriptionService subscriptionService;
    private final CMonetizeOrderRepository orderRepository;

    @RabbitListener(queues = RabbitConfig.QUEUE_C_PAYMENT_SUCCESS)
    public void onPaymentSuccess(Map<String, Object> event) {
        String paymentNo = (String) event.get("paymentNo");
        String bizOrderNo = (String) event.get("bizOrderNo");
        log.info("[CMonetize] Payment success event: paymentNo={}, bizOrderNo={}", paymentNo, bizOrderNo);

        cMonetizeService.confirmPayment(paymentNo, bizOrderNo);

        // Activate subscription if this was a membership order
        orderRepository.findByOrderNo(bizOrderNo).ifPresent(order -> {
            if (order.getProductType() == CMonetizeOrder.ProductType.MEMBERSHIP) {
                subscriptionService.activateSubscription(order.getUserId(), order.getProductId(), bizOrderNo);
            }
        });
    }

    @RabbitListener(queues = RabbitConfig.QUEUE_C_PAYMENT_FAILED)
    public void onPaymentFailed(Map<String, Object> event) {
        String bizOrderNo = (String) event.get("bizOrderNo");
        log.warn("[CMonetize] Payment failed event: bizOrderNo={}", bizOrderNo);
        orderRepository.findByOrderNo(bizOrderNo).ifPresent(order -> {
            order.setStatus(CMonetizeOrder.OrderStatus.EXPIRED);
            orderRepository.save(order);
        });
    }
}
