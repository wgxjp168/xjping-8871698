package com.ilbuy.shop.entity;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class ShopScoreItem {
    private Long   id;
    private Long   mainId;
    private Long   shopId;
    private Integer scoreRule;
    private BigDecimal fullScore;
    private BigDecimal actualScore;
    private String remark;
    private LocalDateTime createTime;
}
