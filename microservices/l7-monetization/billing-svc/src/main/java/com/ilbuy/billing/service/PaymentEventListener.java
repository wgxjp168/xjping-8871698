package com.ilbuy.billing.service;

import com.ilbuy.billing.domain.RefundRecord;
import com.ilbuy.billing.domain.RefundRecord.RefundStatus;
import com.ilbuy.billing.repository.RefundRecordRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Map;

@Component
@RequiredArgsConstructor
@Slf4j
public class PaymentEventListener {

    private final BillingService billingService;
    private final RefundRecordRepository refundRecordRepository;

    /**
     * Listens for payment success events and auto-issues an invoice.
     * Expected message map keys: paymentNo, bizOrderNo, orderType, userId, corpId, amount
     */
    @RabbitListener(queues = "payment.success.billing")
    @Transactional
    public void handlePaymentSuccess(Map<String, Object> message) {
        log.info("Received payment.success.billing event: {}", message);
        try {
            String paymentNo    = (String) message.get("paymentNo");
            String bizOrderNo   = (String) message.get("bizOrderNo");
            String orderType    = (String) message.getOrDefault("orderType", "C_ORDER");
            Long   userId       = message.get("userId")  != null ? Long.valueOf(message.get("userId").toString())  : null;
            Long   corpId       = message.get("corpId")  != null ? Long.valueOf(message.get("corpId").toString())  : null;
            BigDecimal amount   = new BigDecimal(message.get("amount").toString());

            billingService.handlePaymentSuccess(paymentNo, bizOrderNo, orderType, userId, corpId, amount);
        } catch (Exception e) {
            log.error("Failed to process payment.success.billing event: {}", e.getMessage(), e);
        }
    }

    /**
     * Listens for refund success events and marks the RefundRecord as COMPLETED.
     * Expected message map keys: refundNo or paymentNo
     */
    @RabbitListener(queues = "refund.success")
    @Transactional
    public void handleRefundSuccess(Map<String, Object> message) {
        log.info("Received refund.success event: {}", message);
        try {
            String refundNo = message.get("refundNo") != null ? (String) message.get("refundNo") : null;
            String paymentNo = message.get("paymentNo") != null ? (String) message.get("paymentNo") : null;

            RefundRecord record = null;
            if (refundNo != null) {
                record = refundRecordRepository.findByRefundNo(refundNo).orElse(null);
            }
            if (record == null && paymentNo != null) {
                record = refundRecordRepository.findByPaymentNo(paymentNo).orElse(null);
            }
            if (record == null) {
                log.warn("No refund record found for event: {}", message);
                return;
            }
            record.setStatus(RefundStatus.COMPLETED);
            record.setProcessedAt(LocalDateTime.now());
            refundRecordRepository.save(record);
            log.info("Refund {} marked as COMPLETED", record.getRefundNo());
        } catch (Exception e) {
            log.error("Failed to process refund.success event: {}", e.getMessage(), e);
        }
    }
}
