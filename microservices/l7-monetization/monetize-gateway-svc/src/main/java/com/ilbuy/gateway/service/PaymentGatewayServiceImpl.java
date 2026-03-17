package com.ilbuy.gateway.service;

import com.ilbuy.gateway.config.RabbitConfig;
import com.ilbuy.gateway.domain.PaymentOrder;
import com.ilbuy.gateway.domain.PaymentOrder.*;
import com.ilbuy.gateway.domain.RefundRecord;
import com.ilbuy.gateway.dto.*;
import com.ilbuy.gateway.repository.PaymentOrderRepository;
import com.ilbuy.gateway.repository.RefundRecordRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

@Service
@RequiredArgsConstructor
@Slf4j
public class PaymentGatewayServiceImpl implements PaymentGatewayService {

    private final PaymentOrderRepository paymentOrderRepository;
    private final RefundRecordRepository refundRecordRepository;
    private final WechatPayGateway wechatPayGateway;
    private final AlipayGateway alipayGateway;
    private final UnionPayGateway unionPayGateway;
    private final RabbitTemplate rabbitTemplate;
    private final StringRedisTemplate redisTemplate;

    private static final String IDEMPOTENCY_KEY_PREFIX = "pay:idempotency:";
    private static final long ORDER_EXPIRE_MINUTES = 30;

    @Override
    @Transactional
    public PaymentResponse createPayment(CreatePaymentRequest req) {
        String idempotencyKey = IDEMPOTENCY_KEY_PREFIX + req.getBizOrderNo();
        // Idempotency check
        if (Boolean.TRUE.equals(redisTemplate.hasKey(idempotencyKey))) {
            PaymentOrder existing = paymentOrderRepository
                .findByBizOrderNo(req.getBizOrderNo())
                .orElseThrow(() -> new IllegalStateException("Payment order not found for " + req.getBizOrderNo()));
            return toResponse(existing, null);
        }

        String paymentNo = "PAY-" + UUID.randomUUID().toString().replace("-", "").toUpperCase().substring(0, 16);
        PaymentOrder order = PaymentOrder.builder()
            .paymentNo(paymentNo)
            .bizOrderNo(req.getBizOrderNo())
            .userId(req.getUserId())
            .amount(req.getAmount())
            .channel(req.getChannel())
            .bizType(req.getBizType())
            .subject(req.getSubject())
            .status(PaymentStatus.PENDING)
            .expiredAt(LocalDateTime.now().plusMinutes(ORDER_EXPIRE_MINUTES))
            .build();
        paymentOrderRepository.save(order);

        // Set idempotency key (TTL = order expiry)
        redisTemplate.opsForValue().set(idempotencyKey, paymentNo, ORDER_EXPIRE_MINUTES, TimeUnit.MINUTES);

        // Call channel-specific gateway
        Object channelParams;
        try {
            channelParams = switch (req.getChannel()) {
                case WECHAT -> wechatPayGateway.unifiedOrder(order, req.getChannelUserId());
                case ALIPAY -> alipayGateway.createOrder(order, req.getChannelUserId());
                case UNIONPAY -> unionPayGateway.createOrder(order);
            };
            order.setStatus(PaymentStatus.PAYING);
            paymentOrderRepository.save(order);
        } catch (Exception e) {
            log.error("[PaymentGateway] Channel call failed for {}: {}", paymentNo, e.getMessage());
            order.setStatus(PaymentStatus.FAILED);
            paymentOrderRepository.save(order);
            throw new RuntimeException("Payment channel error: " + e.getMessage(), e);
        }

        log.info("[PaymentGateway] Payment created: paymentNo={}, channel={}, amount={}", paymentNo, req.getChannel(), req.getAmount());
        return toResponse(order, channelParams);
    }

    @Override
    @Transactional(readOnly = true)
    public PaymentResponse queryPayment(String paymentNo) {
        PaymentOrder order = paymentOrderRepository.findByPaymentNo(paymentNo)
            .orElseThrow(() -> new IllegalArgumentException("Payment not found: " + paymentNo));
        return toResponse(order, null);
    }

    @Override
    @Transactional
    public RefundResponse applyRefund(RefundRequest req) {
        PaymentOrder payment = paymentOrderRepository.findByPaymentNo(req.getPaymentNo())
            .orElseThrow(() -> new IllegalArgumentException("Payment not found: " + req.getPaymentNo()));

        if (payment.getStatus() != PaymentStatus.SUCCESS) {
            throw new IllegalStateException("Cannot refund payment in status: " + payment.getStatus());
        }
        if (req.getRefundAmount().compareTo(payment.getAmount()) > 0) {
            throw new IllegalArgumentException("Refund amount exceeds payment amount");
        }

        String refundNo = "REF-" + UUID.randomUUID().toString().replace("-", "").toUpperCase().substring(0, 16);
        RefundRecord refund = RefundRecord.builder()
            .refundNo(refundNo)
            .paymentNo(req.getPaymentNo())
            .bizOrderNo(payment.getBizOrderNo())
            .refundAmount(req.getRefundAmount())
            .reason(req.getReason())
            .status(RefundRecord.RefundStatus.PENDING)
            .build();
        refundRecordRepository.save(refund);

        payment.setStatus(PaymentStatus.REFUNDING);
        paymentOrderRepository.save(payment);

        // Async refund call via channel
        try {
            String channelRefundNo = switch (payment.getChannel()) {
                case WECHAT -> wechatPayGateway.refund(payment.getChannelOrderNo(), refundNo, req.getRefundAmount(), payment.getAmount());
                case ALIPAY -> alipayGateway.refund(payment.getChannelOrderNo(), refundNo, req.getRefundAmount());
                case UNIONPAY -> unionPayGateway.refund(payment.getChannelOrderNo(), refundNo, req.getRefundAmount());
            };
            refund.setChannelRefundNo(channelRefundNo);
            refund.setStatus(RefundRecord.RefundStatus.SUCCESS);
            refund.setRefundedAt(LocalDateTime.now());
            payment.setStatus(PaymentStatus.REFUNDED);
            refundRecordRepository.save(refund);
            paymentOrderRepository.save(payment);
            rabbitTemplate.convertAndSend(RabbitConfig.EXCHANGE_PAYMENT, "refund.success." + payment.getBizType().name().toLowerCase(),
                Map.of("refundNo", refundNo, "paymentNo", req.getPaymentNo(), "amount", req.getRefundAmount().toPlainString()));
        } catch (Exception e) {
            log.error("[PaymentGateway] Refund failed for {}: {}", refundNo, e.getMessage());
            refund.setStatus(RefundRecord.RefundStatus.FAILED);
            refundRecordRepository.save(refund);
        }

        return RefundResponse.builder()
            .refundNo(refundNo).paymentNo(req.getPaymentNo())
            .refundAmount(req.getRefundAmount()).status(refund.getStatus())
            .createdAt(refund.getCreatedAt()).build();
    }

    @Override
    @Transactional
    public String handleCallback(String channel, Map<String, String> params, String rawBody) {
        try {
            String channelOrderNo;
            String paymentStatus;
            String bizOrderNo;

            switch (channel.toUpperCase()) {
                case "WECHAT" -> {
                    channelOrderNo = params.get("transaction_id");
                    bizOrderNo = params.get("out_trade_no");
                    paymentStatus = params.get("result_code");
                    if (!wechatPayGateway.verifySignature(params)) return "FAIL";
                }
                case "ALIPAY" -> {
                    channelOrderNo = params.get("trade_no");
                    bizOrderNo = params.get("out_trade_no");
                    paymentStatus = params.get("trade_status");
                    if (!alipayGateway.verifySignature(params)) return "FAIL";
                }
                default -> { return "FAIL"; }
            }

            PaymentOrder order = paymentOrderRepository.findByBizOrderNo(bizOrderNo).orElse(null);
            if (order == null) { log.warn("[Callback] Order not found: {}", bizOrderNo); return "SUCCESS"; }
            if (order.getStatus() == PaymentOrder.PaymentStatus.SUCCESS) return "SUCCESS"; // idempotent

            boolean success = "SUCCESS".equalsIgnoreCase(paymentStatus) || "TRADE_SUCCESS".equalsIgnoreCase(paymentStatus);
            order.setChannelOrderNo(channelOrderNo);
            order.setChannelResp(rawBody);
            order.setStatus(success ? PaymentOrder.PaymentStatus.SUCCESS : PaymentOrder.PaymentStatus.FAILED);
            if (success) order.setPaidAt(LocalDateTime.now());
            paymentOrderRepository.save(order);

            String routingKey = (success ? "payment.success." : "payment.failed.") + order.getBizType().name().toLowerCase();
            rabbitTemplate.convertAndSend(RabbitConfig.EXCHANGE_PAYMENT, routingKey,
                Map.of("paymentNo", order.getPaymentNo(), "bizOrderNo", bizOrderNo,
                       "amount", order.getAmount().toPlainString(), "bizType", order.getBizType().name()));

            log.info("[Callback] Payment {} for bizOrderNo={}", success ? "SUCCESS" : "FAILED", bizOrderNo);
            return "SUCCESS";
        } catch (Exception e) {
            log.error("[Callback] Processing error: {}", e.getMessage(), e);
            return "FAIL";
        }
    }

    private PaymentResponse toResponse(PaymentOrder order, Object channelParams) {
        return PaymentResponse.builder()
            .paymentNo(order.getPaymentNo()).bizOrderNo(order.getBizOrderNo())
            .amount(order.getAmount()).status(order.getStatus())
            .channel(order.getChannel()).channelPayParams(channelParams)
            .expiredAt(order.getExpiredAt()).createdAt(order.getCreatedAt()).build();
    }
}
