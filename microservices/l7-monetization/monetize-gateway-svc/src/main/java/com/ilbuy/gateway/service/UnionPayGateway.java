package com.ilbuy.gateway.service;

import com.ilbuy.gateway.domain.PaymentOrder;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import java.math.BigDecimal;
import java.util.Map;

/**
 * UnionPay QuickPass integration.
 */
@Service
@Slf4j
public class UnionPayGateway {

    @Value("${ilbuy.payment.unionpay.mer-id:}")
    private String merId;

    @Value("${ilbuy.payment.unionpay.notify-url:}")
    private String notifyUrl;

    public Map<String, Object> createOrder(PaymentOrder order) {
        log.info("[UnionPay] Creating order: paymentNo={}", order.getPaymentNo());
        return Map.of(
            "orderId", order.getBizOrderNo(),
            "txnAmt", order.getAmount().multiply(BigDecimal.valueOf(100)).longValue(),
            "tn", "UP_TN_" + System.currentTimeMillis()
        );
    }

    public String refund(String origQryId, String refundNo, BigDecimal refundAmount) {
        log.info("[UnionPay] Refund: origQryId={}, refundNo={}", origQryId, refundNo);
        return "UP_REFUND_" + refundNo;
    }
}
