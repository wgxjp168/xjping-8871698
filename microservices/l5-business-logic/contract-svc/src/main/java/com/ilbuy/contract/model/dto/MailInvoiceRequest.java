package com.ilbuy.contract.model.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class MailInvoiceRequest {

    @NotBlank(message = "快递单号不能为空")
    private String trackingNo;
}
