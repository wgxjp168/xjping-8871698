package com.ilbuy.supplier.model.dto;

import com.ilbuy.supplier.model.enums.SupplierStatus;
import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Builder
public class SupplierDTO {

    private Long id;
    private String supplierNo;
    private String companyName;
    private String contactName;
    private String contactEmail;
    private String contactPhone;
    private String businessLicense;
    private SupplierStatus status;
    private BigDecimal averageScore;
    private Integer totalCoopCount;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
