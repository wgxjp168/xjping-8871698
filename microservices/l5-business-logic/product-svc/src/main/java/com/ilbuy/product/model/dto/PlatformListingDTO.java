package com.ilbuy.product.model.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PlatformListingDTO {

    private Long id;
    private String canonicalId;
    private String platform;
    private String externalUrl;
    private BigDecimal currentPrice;
    private BigDecimal originalPrice;
    private String currency;
    private Boolean inStock;
    private Instant lastSyncAt;
}
