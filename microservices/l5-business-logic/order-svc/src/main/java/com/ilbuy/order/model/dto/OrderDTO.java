package com.ilbuy.order.model.dto;

import com.ilbuy.order.model.enums.OrderScene;
import com.ilbuy.order.model.enums.OrderStatus;
import com.ilbuy.order.model.enums.PaymentMethod;
import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

@Data
@Builder
public class OrderDTO {
    private Long id;
    private String orderNo;
    private Long userId;
    private OrderStatus status;
    private BigDecimal totalAmount;
    private BigDecimal discountAmount;
    private BigDecimal finalAmount;
    private PaymentMethod paymentMethod;
    private String shippingName;
    private String shippingPhone;
    private String shippingAddress;
    private String shippingCity;
    private String shippingProvince;
    private String remark;
    private String cancelReason;
    // 场景区分
    private OrderScene scene;
    // B2B
    private String contractNo;
    private Boolean invoiceRequired;
    private String invoiceTitle;
    private String taxpayerId;
    private String supplierNo;
    // B2C
    private String couponCode;
    private Long flashSaleId;
    private Instant paidAt;
    private Instant shippedAt;
    private Instant deliveredAt;
    private Instant cancelledAt;
    private Instant createdAt;
    private List<OrderItemDTO> items;
}
