package com.ilbuy.price.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PriceTrendDTO {

    private Long canonicalId;
    private String platform;

    /**
     * Granularity: DAILY, WEEKLY, MONTHLY
     */
    private String granularity;

    private List<TrendPointDTO> points;
}
