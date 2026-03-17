package com.ilbuy.bmonetize.service;

import com.ilbuy.bmonetize.config.RabbitConfig;
import com.ilbuy.bmonetize.domain.BMonetizeOrder;
import com.ilbuy.bmonetize.repository.BMonetizeOrderRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Service;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class PaymentEventListener {

    private final BMonetizeService bMonetizeService;
    private final BMonetizeOrderRepository orderRepository;

    @RabbitListener(queues = RabbitConfig.QUEUE_B_PAYMENT_SUCCESS)
    public void onPaymentSuccess(Map<String, Object> event) {
        String paymentNo = (String) event.get("paymentNo");
        String bizOrderNo = (String) event.get("bizOrderNo");
        log.info("[BMonetize] Payment success event: paymentNo={}, bizOrderNo={}", paymentNo, bizOrderNo);
        bMonetizeService.confirmPayment(paymentNo, bizOrderNo);
    }

    @RabbitListener(queues = RabbitConfig.QUEUE_B_PAYMENT_FAILED)
    public void onPaymentFailed(Map<String, Object> event) {
        String bizOrderNo = (String) event.get("bizOrderNo");
        log.warn("[BMonetize] Payment failed: bizOrderNo={}", bizOrderNo);
        orderRepository.findByOrderNo(bizOrderNo).ifPresent(order -> {
            order.setStatus(BMonetizeOrder.OrderStatus.EXPIRED);
            orderRepository.save(order);
        });
    }
}
