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
public class PricePointDTO {

    private BigDecimal price;
    private BigDecimal originalPrice;
    private LocalDateTime recordedAt;
}
