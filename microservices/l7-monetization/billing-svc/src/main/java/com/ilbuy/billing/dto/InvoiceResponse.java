package com.ilbuy.billing.dto;

import com.ilbuy.billing.domain.Invoice.InvoiceStatus;
import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Builder
public class InvoiceResponse {

    private String invoiceNo;
    private Long userId;
    private Long corpId;
    private String orderNo;
    private String orderType;
    private BigDecimal amount;
    private String currency;
    private InvoiceStatus status;
    private LocalDateTime issuedAt;
    private LocalDateTime createdAt;
}
