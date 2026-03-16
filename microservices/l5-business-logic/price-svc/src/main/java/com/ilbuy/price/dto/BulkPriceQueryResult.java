package com.ilbuy.price.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BulkPriceQueryResult {

    private String canonicalId;
    private String platform;
    private int quantity;
    private BigDecimal unitPrice;
    private BigDecimal totalAmount;
    private String currency;
    private String unit;
    private BulkPriceTierDTO tierApplied;
    private List<BulkPriceTierDTO> allTiers;
}
