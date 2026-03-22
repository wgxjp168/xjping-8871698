package com.ilbuy.shop.vo;

import com.alibaba.excel.annotation.ExcelProperty;
import lombok.Data;
import java.time.LocalDateTime;

@Data
public class ShopViolationVO {

    @ExcelProperty("违规ID")
    private Long id;

    @ExcelProperty("商铺ID")
    private Long shopId;

    @ExcelProperty("商铺名称")
    private String shopName;

    @ExcelProperty("违规类型")
    private String vioType;

    @ExcelProperty("违规内容")
    private String vioContent;

    @ExcelProperty("违规时间")
    private LocalDateTime vioTime;

    @ExcelProperty("扣分")
    private Integer deductionScore;

    @ExcelProperty("处理结果")
    private String handleResult;

    @ExcelProperty("创建时间")
    private LocalDateTime createTime;
}
