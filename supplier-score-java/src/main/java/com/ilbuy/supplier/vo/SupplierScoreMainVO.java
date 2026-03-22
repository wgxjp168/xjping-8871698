package com.ilbuy.supplier.vo;

import com.alibaba.excel.annotation.ExcelProperty;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class SupplierScoreMainVO {

    @ExcelProperty("评分ID")
    private Long mainId;

    @ExcelProperty("供应商ID")
    private Long supplierId;

    @ExcelProperty("供应商名称")
    private String supplierName;

    @ExcelProperty("评分周期")
    private String scorePeriod;

    @ExcelProperty("总分")
    private BigDecimal totalScore;

    @ExcelProperty("等级")
    private String supplierLevel;

    @ExcelProperty("评分人")
    private String scoreUser;

    @ExcelProperty("评分时间")
    private LocalDateTime scoreTime;

    @ExcelProperty("评语")
    private String opinion;

    @ExcelProperty("创建时间")
    private LocalDateTime createTime;
}
