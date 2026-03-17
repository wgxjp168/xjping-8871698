package com.ilbuy.gateway.dto;

import com.ilbuy.gateway.domain.PaymentOrder.PaymentChannel;
import com.ilbuy.gateway.domain.PaymentOrder.PaymentStatus;
import lombok.Builder;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data @Builder
public class PaymentResponse {
    private String paymentNo;
    private String bizOrderNo;
    private BigDecimal amount;
    private PaymentStatus status;
    private PaymentChannel channel;
    /** Channel-specific payment params (e.g., WeChat prepay_id, Alipay form) */
    private Object channelPayParams;
    private LocalDateTime expiredAt;
    private LocalDateTime createdAt;
}
