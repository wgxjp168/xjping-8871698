package com.ilbuy.datamonetize.service;

import com.ilbuy.datamonetize.config.RabbitConfig;
import com.ilbuy.datamonetize.domain.DataOrder;
import com.ilbuy.datamonetize.repository.DataOrderRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class PaymentEventListener {

    private final DataMonetizeService dataMonetizeService;
    private final DataOrderRepository orderRepository;

    @RabbitListener(queues = RabbitConfig.QUEUE_DATA_PAYMENT_SUCCESS)
    public void onPaymentSuccess(Map<String, Object> event) {
        String paymentNo = (String) event.get("paymentNo");
        String bizOrderNo = (String) event.get("bizOrderNo");
        log.info("[DataMonetize] Payment success event: paymentNo={}, bizOrderNo={}", paymentNo, bizOrderNo);
        dataMonetizeService.confirmPayment(paymentNo, bizOrderNo);
    }

    @RabbitListener(queues = RabbitConfig.QUEUE_DATA_PAYMENT_FAILED)
    public void onPaymentFailed(Map<String, Object> event) {
        String bizOrderNo = (String) event.get("bizOrderNo");
        log.warn("[DataMonetize] Payment failed event: bizOrderNo={}", bizOrderNo);
        orderRepository.findByOrderNo(bizOrderNo).ifPresent(order -> {
            order.setStatus(DataOrder.OrderStatus.CANCELLED);
            orderRepository.save(order);
            log.info("[DataMonetize] Order cancelled due to payment failure: orderNo={}", bizOrderNo);
        });
    }
}
