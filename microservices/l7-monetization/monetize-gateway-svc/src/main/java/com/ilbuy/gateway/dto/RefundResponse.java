package com.ilbuy.gateway.dto;

import com.ilbuy.gateway.domain.RefundRecord.RefundStatus;
import lombok.Builder;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data @Builder
public class RefundResponse {
    private String refundNo;
    private String paymentNo;
    private BigDecimal refundAmount;
    private RefundStatus status;
    private LocalDateTime createdAt;
}
