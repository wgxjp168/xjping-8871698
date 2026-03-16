package com.ilbuy.order.model.dto;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;

@Data
@Builder
public class OrderItemDTO {
    private Long id;
    private String canonicalId;
    private String platform;
    private String productTitle;
    private BigDecimal unitPrice;
    private Integer quantity;
    private BigDecimal subtotal;
    private String specs;
    private String imageUrl;
}
