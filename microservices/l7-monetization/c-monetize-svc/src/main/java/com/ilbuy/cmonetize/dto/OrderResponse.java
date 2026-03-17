package com.ilbuy.cmonetize.dto;

import com.ilbuy.cmonetize.domain.CMonetizeOrder.*;
import lombok.Builder;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data @Builder
public class OrderResponse {
    private String orderNo;
    private Long userId;
    private ProductType productType;
    private String productId;
    private BigDecimal amount;
    private OrderStatus status;
    private String paymentNo;
    private Object channelPayParams;
    private LocalDateTime createdAt;
    private LocalDateTime expiredAt;
}
