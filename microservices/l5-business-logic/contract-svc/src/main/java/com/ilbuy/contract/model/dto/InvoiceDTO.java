package com.ilbuy.contract.model.dto;

import com.ilbuy.contract.model.enums.InvoiceStatus;
import com.ilbuy.contract.model.enums.InvoiceType;
import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@Builder
public class InvoiceDTO {

    private Long id;
    private String invoiceNo;
    private Long contractId;
    private Long userId;
    private InvoiceType type;
    private BigDecimal amount;
    private BigDecimal taxRate;
    private BigDecimal taxAmount;
    private String invoiceTitle;
    private String taxpayerId;
    private String bankAccount;
    private String bankName;
    private String companyAddress;
    private InvoiceStatus status;
    private LocalDate issueDate;
    private String mailingAddress;
    private String trackingNo;
    private LocalDateTime createdAt;
}
