package com.ilbuy.bmonetize.dto;

import com.ilbuy.bmonetize.domain.BMonetizeOrder.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data @Builder
public class BOrderResponse {
    private String orderNo;
    private Long corpId;
    private ProductType productType;
    private String productId;
    private BigDecimal amount;
    private OrderStatus status;
    private String paymentNo;
    private String contractNo;
    private Object channelPayParams;
    private LocalDateTime createdAt;
}
