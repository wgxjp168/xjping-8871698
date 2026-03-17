package com.ilbuy.cmonetize.dto;

import jakarta.validation.constraints.*;
import lombok.Data;

@Data
public class SubscribeRequest {
    @NotNull
    private Long userId;

    @NotBlank
    private String planCode;

    @NotBlank
    private String paymentChannel;

    private String channelUserId;

    private Boolean autoRenew = false;
}
