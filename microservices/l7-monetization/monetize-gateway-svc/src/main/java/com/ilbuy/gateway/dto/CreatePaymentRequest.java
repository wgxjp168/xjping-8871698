package com.ilbuy.gateway.dto;

import com.ilbuy.gateway.domain.PaymentOrder.BizType;
import com.ilbuy.gateway.domain.PaymentOrder.PaymentChannel;
import jakarta.validation.constraints.*;
import lombok.Data;
import java.math.BigDecimal;

@Data
public class CreatePaymentRequest {

    @NotBlank
    private String bizOrderNo;

    @NotNull
    private Long userId;

    @NotNull
    @DecimalMin("0.01")
    private BigDecimal amount;

    @NotNull
    private PaymentChannel channel;

    @NotNull
    private BizType bizType;

    @NotBlank
    @Size(max = 256)
    private String subject;

    /** Wechat: openId; Alipay: buyerLogonId; UnionPay: not required */
    private String channelUserId;

    /** Optional notify URL override */
    private String notifyUrl;
}
