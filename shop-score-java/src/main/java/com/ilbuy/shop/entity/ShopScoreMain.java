package com.ilbuy.shop.entity;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class ShopScoreMain {
    private Long   mainId;
    private Long   shopId;
    private String scorePeriod;
    private BigDecimal totalScore;
    private String shopLevel;
    private String scoreUser;
    private LocalDateTime scoreTime;
    private String opinion;
    private LocalDateTime createTime;
}
