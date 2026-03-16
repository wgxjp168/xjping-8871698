package com.ilbuy.contract.model.dto;

import com.ilbuy.contract.model.enums.ContractStatus;
import com.ilbuy.contract.model.enums.ContractType;
import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@Builder
public class ContractDTO {

    private Long id;
    private String contractNo;
    private Long orderId;
    private Long buyerUserId;
    private String supplierNo;
    private String title;
    private ContractType type;
    private ContractStatus status;
    private String fileUrl;
    private LocalDateTime signedAt;
    private LocalDate expiresAt;
    private BigDecimal totalAmount;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
