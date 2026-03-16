package com.ilbuy.order.model.dto;

import com.ilbuy.order.model.enums.PaymentMethod;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import lombok.Data;

import java.util.List;

@Data
public class CreateOrderRequest {

    @NotEmpty
    @Valid
    private List<OrderItemRequest> items;

    @NotNull
    private PaymentMethod paymentMethod;

    @NotBlank
    private String shippingName;

    @NotBlank
    @Pattern(regexp = "^1[3-9]\\d{9}$")
    private String shippingPhone;

    @NotBlank
    private String shippingAddress;

    @NotBlank
    private String shippingCity;

    @NotBlank
    private String shippingProvince;

    private String remark;

    @Data
    public static class OrderItemRequest {

        @NotBlank
        private String canonicalId;

        @NotBlank
        private String platform;

        @NotBlank
        private String productTitle;

        @NotNull
        @Positive
        private java.math.BigDecimal unitPrice;

        @NotNull
        @Min(1)
        private Integer quantity;

        private String specs;
        private String imageUrl;
    }
}
