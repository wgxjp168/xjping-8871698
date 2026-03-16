package com.ilbuy.recommend.dto;

import com.ilbuy.recommend.model.enums.RecommendSource;
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
public class RecommendItemDTO {

    private Long id;
    private Long canonicalId;
    private String platform;
    private String productTitle;
    private String imageUrl;
    private BigDecimal currentPrice;
    private Double score;
    private RecommendSource source;
    private LocalDateTime createdAt;
    private LocalDateTime expiresAt;
}
