package com.ilbuy.price.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BulkPriceTierDTO {

    private String canonicalId;
    private String platform;
    private Integer minQuantity;
    private Integer maxQuantity;
    private BigDecimal unitPrice;
    private String currency;
    private String unit;
    private LocalDate validFrom;
    private LocalDate validUntil;
}
