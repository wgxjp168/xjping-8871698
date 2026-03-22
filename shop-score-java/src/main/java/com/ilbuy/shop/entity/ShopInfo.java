package com.ilbuy.shop.entity;

import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
public class ShopInfo {
    private Long   shopId;
    private String shopName;
    private Integer cateId;
    private String contactUser;
    private String contactPhone;
    private Integer shopStatus;
    private LocalDate joinTime;
    private String remark;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
