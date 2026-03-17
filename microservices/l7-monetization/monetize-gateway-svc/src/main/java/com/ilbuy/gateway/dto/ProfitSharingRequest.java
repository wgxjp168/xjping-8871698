package com.ilbuy.gateway.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;
import java.math.BigDecimal;
import java.util.List;

@Data
public class ProfitSharingRequest {

    @NotBlank
    private String paymentNo;

    /** Sharing recipients */
    @NotEmpty
    private List<Receiver> receivers;

    @Data
    public static class Receiver {
        /** WeChat: receiver's openid or merchant_id; Alipay: login_id */
        @NotBlank
        private String account;

        /** Type: MERCHANT_ID / PERSONAL_OPENID / PERSONAL_SUB_OPENID */
        private String type;

        /** Amount in CNY */
        private BigDecimal amount;

        /** Description shown in the sharing record */
        private String description;
    }
}
