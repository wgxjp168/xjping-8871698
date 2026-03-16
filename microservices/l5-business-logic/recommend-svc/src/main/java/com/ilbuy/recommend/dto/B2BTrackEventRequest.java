package com.ilbuy.recommend.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.math.BigDecimal;

/**
 * B2B-specific behavior event request.
 * Captures procurement actions distinct from B2C browsing events.
 * Supported eventTypes: PROCUREMENT_VIEW / RFQ_SUBMIT / BULK_ORDER / CONTRACT_SIGN
 */
@Data
public class B2BTrackEventRequest {

    @NotBlank(message = "eventType is required")
    private String eventType;  // PROCUREMENT_VIEW / RFQ_SUBMIT / BULK_ORDER / CONTRACT_SIGN

    private String canonicalId;

    private String supplierNo;

    private String category;

    private Integer quantity;

    private BigDecimal amount;
}
