package com.ilbuy.billing.dto;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.math.BigDecimal;

@Data
public class CreateRefundRequest {

    @NotBlank
    private String originalOrderNo;

    @NotBlank
    private String paymentNo;

    private Long userId;

    private Long corpId;

    @NotNull
    @DecimalMin("0.01")
    private BigDecimal refundAmount;

    @NotBlank
    private String reason;
}
