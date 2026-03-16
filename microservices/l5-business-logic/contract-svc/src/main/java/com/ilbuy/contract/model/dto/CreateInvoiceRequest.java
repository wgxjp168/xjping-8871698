package com.ilbuy.contract.model.dto;

import com.ilbuy.contract.model.enums.InvoiceType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CreateInvoiceRequest {

    @NotNull(message = "合同ID不能为空")
    private Long contractId;

    @NotNull(message = "发票类型不能为空")
    private InvoiceType type;

    @NotBlank(message = "发票抬头不能为空")
    private String invoiceTitle;

    private String taxpayerId;

    private String bankAccount;

    private String bankName;

    private String companyAddress;

    private String mailingAddress;
}
