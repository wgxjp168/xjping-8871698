package com.ilbuy.price.dto;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.math.BigDecimal;

@Data
public class CreateAlertRequest {

    @NotNull(message = "canonicalId is required")
    private Long canonicalId;

    private String platform;

    @NotNull(message = "targetPrice is required")
    @DecimalMin(value = "0.01", message = "targetPrice must be positive")
    private BigDecimal targetPrice;
}
