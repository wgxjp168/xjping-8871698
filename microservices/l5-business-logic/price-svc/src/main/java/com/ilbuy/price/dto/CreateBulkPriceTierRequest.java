package com.ilbuy.price.dto;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;

@Data
public class CreateBulkPriceTierRequest {

    @NotBlank(message = "canonicalId is required")
    private String canonicalId;

    @NotBlank(message = "platform is required")
    private String platform;

    @NotNull(message = "minQuantity is required")
    @Min(value = 1, message = "minQuantity must be at least 1")
    private Integer minQuantity;

    private Integer maxQuantity;

    @NotNull(message = "unitPrice is required")
    @DecimalMin(value = "0.01", message = "unitPrice must be positive")
    private BigDecimal unitPrice;

    private String currency;

    private String unit;

    private LocalDate validFrom;

    private LocalDate validUntil;
}
