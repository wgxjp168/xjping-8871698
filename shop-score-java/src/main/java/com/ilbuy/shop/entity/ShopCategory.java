package com.ilbuy.shop.entity;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class ShopCategory {
    private Integer id;
    private String  cateName;
    private Integer sort;
    private Integer status;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
