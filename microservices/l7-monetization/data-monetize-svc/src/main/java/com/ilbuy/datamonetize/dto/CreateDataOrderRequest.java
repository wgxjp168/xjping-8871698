package com.ilbuy.datamonetize.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CreateDataOrderRequest {

    @NotNull(message = "userId is required")
    private Long userId;

    private Long corpId; // nullable, for B-end

    @NotBlank(message = "productCode is required")
    private String productCode;

    private Integer quantity = 1;

    @NotBlank(message = "paymentChannel is required")
    private String paymentChannel;

    private String channelUserId; // nullable
}
