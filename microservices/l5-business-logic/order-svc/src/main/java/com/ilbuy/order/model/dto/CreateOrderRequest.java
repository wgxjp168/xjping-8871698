package com.ilbuy.order.model.dto;

import com.ilbuy.order.model.enums.OrderScene;
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

    /** 业务场景，默认 B2C */
    private OrderScene scene = OrderScene.B2C;

    // ── B2B 专属（scene=B2B 时有效）────────────────────────────

    /** 关联合同编号（B2B 可选） */
    private String contractNo;

    /** 是否需要开具增值税专用发票 */
    private Boolean invoiceRequired = false;

    /** 开票抬头（invoiceRequired=true 时必填） */
    private String invoiceTitle;

    /** 纳税人识别号（invoiceRequired=true 时必填） */
    private String taxpayerId;

    /** 供应商编号（B2B 采购来源） */
    private String supplierNo;

    // ── B2C 专属（scene=B2C 时有效）────────────────────────────

    /** 优惠券码 */
    private String couponCode;

    /** 闪购活动 ID */
    private Long flashSaleId;

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
