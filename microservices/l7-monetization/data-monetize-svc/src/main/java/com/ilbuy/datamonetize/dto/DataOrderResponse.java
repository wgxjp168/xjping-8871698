package com.ilbuy.datamonetize.dto;

import com.ilbuy.datamonetize.domain.DataOrder.OrderStatus;
import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Builder
public class DataOrderResponse {

    private String orderNo;
    private Long userId;
    private Long corpId;
    private String productCode;
    private String productName;
    private BigDecimal unitPrice;
    private Integer quantity;
    private BigDecimal totalAmount;
    private OrderStatus status;
    private String paymentNo;
    private Object channelPayParams;
    private LocalDateTime createdAt;
}
