package com.ilbuy.shop.entity;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class ShopOperateLog {
    private Long   id;
    private Long   shopId;
    private String operateType;
    private String operateContent;
    private String operateUser;
    private LocalDateTime operateTime;
}
