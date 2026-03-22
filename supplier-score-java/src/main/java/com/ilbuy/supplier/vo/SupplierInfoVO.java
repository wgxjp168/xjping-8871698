package com.ilbuy.supplier.vo;

import com.alibaba.excel.annotation.ExcelProperty;
import lombok.Data;

import java.time.LocalDateTime;

@Data
public class SupplierInfoVO {

    @ExcelProperty("供应商ID")
    private Long supplierId;

    @ExcelProperty("供应商名称")
    private String supplierName;

    @ExcelProperty("分类名称")
    private String cateName;

    @ExcelProperty("统一社会信用代码")
    private String creditCode;

    @ExcelProperty("联系人")
    private String contactUser;

    @ExcelProperty("联系电话")
    private String contactPhone;

    @ExcelProperty("地址")
    private String address;

    @ExcelProperty("资质说明")
    private String qualification;

    @ExcelProperty("状态")
    private String supplierStatusName;

    @ExcelProperty("创建时间")
    private LocalDateTime createTime;
}
