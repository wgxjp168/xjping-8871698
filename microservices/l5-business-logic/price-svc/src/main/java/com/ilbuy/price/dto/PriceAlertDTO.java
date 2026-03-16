package com.ilbuy.price.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PriceAlertDTO {

    private Long id;
    private Long userId;
    private Long canonicalId;
    private String platform;
    private BigDecimal targetPrice;
    private Boolean triggered;
    private LocalDateTime createdAt;
    private LocalDateTime triggeredAt;
}
