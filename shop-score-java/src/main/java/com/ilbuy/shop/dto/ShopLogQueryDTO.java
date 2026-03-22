package com.ilbuy.shop.dto;

import com.ilbuy.shop.common.PageQuery;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
public class ShopLogQueryDTO extends PageQuery {

    private Long   shopId;
    private String operateType;
    private String operateUser;
    /** 操作时间起 */
    private String operateTimeStart;
    /** 操作时间止 */
    private String operateTimeEnd;
}
