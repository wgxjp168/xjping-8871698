package com.ilbuy.shop.entity;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class ShopViolation {
    private Long   id;
    private Long   shopId;
    private String vioType;
    private String vioContent;
    private LocalDateTime vioTime;
    private Integer deductionScore;
    private String handleResult;
    private LocalDateTime createTime;
}
