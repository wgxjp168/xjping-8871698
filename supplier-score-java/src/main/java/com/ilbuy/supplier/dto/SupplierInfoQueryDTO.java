package com.ilbuy.supplier.dto;

import com.ilbuy.supplier.common.PageQuery;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
public class SupplierInfoQueryDTO extends PageQuery {

    private String supplierName;
    private Integer cateId;
    private Integer supplierStatus;
}
