package com.ilbuy.gateway.service;

import com.ilbuy.gateway.domain.PaymentOrder;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import java.math.BigDecimal;
import java.util.Map;
import java.util.UUID;

/**
 * Alipay integration using App Pay / Page Pay.
 * Production: replace stub methods with alipay-sdk-java.
 */
@Service
@Slf4j
public class AlipayGateway {

    @Value("${ilbuy.payment.alipay.app-id:}")
    private String appId;

    @Value("${ilbuy.payment.alipay.private-key:}")
    private String privateKey;

    @Value("${ilbuy.payment.alipay.alipay-public-key:}")
    private String alipayPublicKey;

    @Value("${ilbuy.payment.alipay.notify-url:}")
    private String notifyUrl;

    /**
     * Create Alipay page/app payment. Returns signed form or payment string.
     */
    public Map<String, Object> createOrder(PaymentOrder order, String buyerLogonId) {
        log.info("[Alipay] Creating order: paymentNo={}, amount={}", order.getPaymentNo(), order.getAmount());
        // TODO: Replace with alipay-sdk-java: AlipayClient.execute(AlipayTradePagePayRequest)
        return Map.of(
            "out_trade_no", order.getBizOrderNo(),
            "total_amount", order.getAmount().toPlainString(),
            "subject", order.getSubject(),
            "payment_form", "<form method='POST'><!-- Alipay form placeholder --></form>"
        );
    }

    public String refund(String tradeNo, String refundNo, BigDecimal refundAmount) {
        log.info("[Alipay] Refund: tradeNo={}, refundNo={}, amount={}", tradeNo, refundNo, refundAmount);
        // TODO: AlipayTradeRefundRequest
        return "ALI_REFUND_" + refundNo;
    }

    public boolean verifySignature(Map<String, String> params) {
        // TODO: AlipaySignature.rsaCheckV1(params, alipayPublicKey, "UTF-8", "RSA2")
        log.debug("[Alipay] Verifying signature");
        return true;
    }
}
