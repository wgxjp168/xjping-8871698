package com.ilbuy.supplier.vo;

import com.alibaba.excel.annotation.ExcelProperty;
import lombok.Data;

import java.time.LocalDateTime;

@Data
public class SupplierLogVO {

    @ExcelProperty("日志ID")
    private Long id;

    @ExcelProperty("供应商ID")
    private Long supplierId;

    @ExcelProperty("供应商名称")
    private String supplierName;

    @ExcelProperty("操作类型")
    private String operateType;

    @ExcelProperty("操作内容")
    private String operateContent;

    @ExcelProperty("操作人")
    private String operateUser;

    @ExcelProperty("操作时间")
    private LocalDateTime operateTime;
}
