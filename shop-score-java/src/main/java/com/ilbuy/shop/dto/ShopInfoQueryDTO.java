package com.ilbuy.shop.dto;

import com.ilbuy.shop.common.PageQuery;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
public class ShopInfoQueryDTO extends PageQuery {

    /** 商铺名称（模糊） */
    private String shopName;

    /** 类目ID */
    private Integer cateId;

    /** 商铺状态 1正常 2暂停 3关闭 */
    private Integer shopStatus;
}
