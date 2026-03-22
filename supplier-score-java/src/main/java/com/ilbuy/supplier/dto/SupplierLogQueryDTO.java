package com.ilbuy.supplier.dto;

import com.ilbuy.supplier.common.PageQuery;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
public class SupplierLogQueryDTO extends PageQuery {

    private Long   supplierId;
    private String operateType;
    private String operateUser;
    /** 操作时间起 yyyy-MM-dd HH:mm:ss */
    private String operateTimeStart;
    /** 操作时间止 */
    private String operateTimeEnd;
}
