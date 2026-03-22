package com.ilbuy.supplier.dto;

import com.ilbuy.supplier.common.PageQuery;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
public class SupplierAbnormalQueryDTO extends PageQuery {

    private Long   supplierId;
    private String supplierName;
    private String abnType;
    /** 异常时间起 yyyy-MM-dd HH:mm:ss */
    private String abnTimeStart;
    /** 异常时间止 */
    private String abnTimeEnd;
}
