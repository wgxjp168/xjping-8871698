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
public class PlatformPriceDTO {

    private String platform;
    private BigDecimal currentPrice;
    private BigDecimal originalPrice;

    /**
     * Discount percentage: e.g. 80 means 80% of original price (20% off).
     */
    private BigDecimal discount;

    private Boolean inStock;
    private LocalDateTime lastUpdated;
}
