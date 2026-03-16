package com.ilbuy.supplier.model.dto.rfq;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RfqQuoteDTO {

    private Long id;
    private Long rfqId;
    private String supplierNo;
    private BigDecimal unitPrice;
    private BigDecimal totalAmount;
    private String currency;
    private Integer deliveryDays;
    private LocalDate validUntil;
    private String paymentTerms;
    private String supplierRemark;
    private LocalDateTime createdAt;
}
