package com.ilbuy.bmonetize.dto;

import com.ilbuy.bmonetize.domain.BMonetizeOrder.ProductType;
import jakarta.validation.constraints.*;
import lombok.Data;
import java.math.BigDecimal;

@Data
public class CreateBOrderRequest {
    @NotNull private Long corpId;
    @NotNull private Long contactUserId;
    @NotNull private ProductType productType;
    @NotBlank private String productId;    // planCode or custom service code
    @NotNull @DecimalMin("0.01") private BigDecimal amount;
    @NotBlank private String paymentChannel;
    private String channelUserId;
}
