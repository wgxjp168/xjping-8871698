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
public class PriceHistoryDTO {

    private Long canonicalId;
    private String platform;
    private List<PricePointDTO> points;
}
