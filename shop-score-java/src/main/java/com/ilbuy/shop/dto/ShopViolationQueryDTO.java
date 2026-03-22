package com.ilbuy.shop.dto;

import com.ilbuy.shop.common.PageQuery;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
public class ShopViolationQueryDTO extends PageQuery {

    private Long   shopId;
    private String shopName;
    private String vioType;
    /** 违规时间起 yyyy-MM-dd HH:mm:ss */
    private String vioTimeStart;
    /** 违规时间止 */
    private String vioTimeEnd;
}
