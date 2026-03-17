package com.ilbuy.billing.dto;

import com.ilbuy.billing.domain.RefundRecord.RefundStatus;
import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Builder
public class RefundResponse {

    private String refundNo;
    private String originalOrderNo;
    private String paymentNo;
    private BigDecimal refundAmount;
    private RefundStatus status;
    private LocalDateTime processedAt;
    private LocalDateTime createdAt;
}
