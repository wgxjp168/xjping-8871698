package com.ilbuy.supplier.model.dto.rfq;

import com.ilbuy.supplier.model.enums.RfqStatus;
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
public class RfqRequestDTO {

    private Long id;
    private String rfqNo;
    private Long buyerUserId;
    private String supplierNo;
    private String productDescription;
    private String canonicalId;
    private Integer quantity;
    private String unit;
    private LocalDate requiredDeliveryDate;
    private String deliveryAddress;
    private BigDecimal budgetAmount;
    private RfqStatus status;
    private String buyerRemark;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private RfqQuoteDTO quote;
}
