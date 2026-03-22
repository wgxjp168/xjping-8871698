package com.ilbuy.supplier.vo;

import com.alibaba.excel.annotation.ExcelProperty;
import lombok.Data;

import java.time.LocalDateTime;

@Data
public class SupplierAbnormalVO {

    @ExcelProperty("异常ID")
    private Long id;

    @ExcelProperty("供应商ID")
    private Long supplierId;

    @ExcelProperty("供应商名称")
    private String supplierName;

    @ExcelProperty("异常类型")
    private String abnType;

    @ExcelProperty("异常内容")
    private String abnContent;

    @ExcelProperty("异常时间")
    private LocalDateTime abnTime;

    @ExcelProperty("扣分")
    private Integer deductionScore;

    @ExcelProperty("处理结果")
    private String handleResult;

    @ExcelProperty("创建时间")
    private LocalDateTime createTime;
}
