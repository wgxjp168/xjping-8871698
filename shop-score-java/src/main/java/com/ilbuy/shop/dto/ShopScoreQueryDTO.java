package com.ilbuy.shop.dto;

import com.ilbuy.shop.common.PageQuery;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
public class ShopScoreQueryDTO extends PageQuery {

    /** 商铺ID */
    private Long shopId;

    /** 商铺名称（模糊） */
    private String shopName;

    /** 评分周期，格式 YYYY-MM */
    private String scorePeriod;

    /** 等级：A/B/C/D */
    private String shopLevel;
}
