package com.ilbuy.recommend.dto;

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
public class UserProfileDTO {

    private Long userId;
    private String preferredCategories;
    private String preferredPlatforms;
    private BigDecimal priceRangeMin;
    private BigDecimal priceRangeMax;
    private Long totalViews;
    private Long totalOrders;
    private LocalDateTime lastActiveAt;
    private LocalDateTime updatedAt;
}
