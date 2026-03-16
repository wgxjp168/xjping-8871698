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
public class CrossPlatformPriceDTO {

    private Long canonicalId;
    private String productTitle;

    /**
     * Platforms sorted by currentPrice ASC.
     */
    private List<PlatformPriceDTO> platforms;

    private String lowestPlatform;
    private BigDecimal lowestPrice;

    /**
     * Price difference: highest price - lowest price.
     */
    private BigDecimal priceDiff;

    /**
     * Price difference percentage relative to lowest price.
     */
    private BigDecimal priceDiffPct;
}
