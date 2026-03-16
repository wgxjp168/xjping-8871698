package com.ilbuy.price.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class BulkPriceQueryRequest {

    @NotBlank(message = "canonicalId is required")
    private String canonicalId;

    private String platform;

    @Min(value = 1, message = "quantity must be at least 1")
    private int quantity;
}
