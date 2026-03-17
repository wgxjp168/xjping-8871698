package com.ilbuy.gateway.dto;

import jakarta.validation.constraints.*;
import lombok.Data;
import java.math.BigDecimal;

@Data
public class RefundRequest {
    @NotBlank
    private String paymentNo;

    @NotNull
    @DecimalMin("0.01")
    private BigDecimal refundAmount;

    @NotBlank
    @Size(max = 256)
    private String reason;
}
