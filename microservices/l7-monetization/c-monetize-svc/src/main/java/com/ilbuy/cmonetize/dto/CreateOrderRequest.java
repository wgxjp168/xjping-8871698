package com.ilbuy.cmonetize.dto;

import com.ilbuy.cmonetize.domain.CMonetizeOrder.ProductType;
import jakarta.validation.constraints.*;
import lombok.Data;
import java.math.BigDecimal;

@Data
public class CreateOrderRequest {
    @NotNull
    private Long userId;

    @NotNull
    private ProductType productType;

    /** SINGLE_REPORT: l6ReportNo; MEMBERSHIP: planCode */
    @NotBlank
    private String productId;

    @NotBlank
    private String paymentChannel;   // WECHAT | ALIPAY | UNIONPAY

    private String channelUserId;    // WeChat openId or Alipay buyerId

    private String l5OrderNo;        // Upstream L5 order reference
}
