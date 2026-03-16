package com.ilbuy.supplier.model.dto;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Builder
public class CooperationScoreDTO {

    private Long id;
    private Long supplierId;
    private Long orderId;
    private Long scoreBy;
    private BigDecimal qualityScore;
    private BigDecimal deliveryScore;
    private BigDecimal serviceScore;
    private BigDecimal overallScore;
    private String comment;
    private LocalDateTime scoredAt;
}
