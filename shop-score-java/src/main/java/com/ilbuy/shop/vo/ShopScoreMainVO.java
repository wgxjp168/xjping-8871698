package com.ilbuy.shop.vo;

import com.alibaba.excel.annotation.ExcelProperty;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class ShopScoreMainVO {

    @ExcelProperty("评分ID")
    private Long mainId;

    @ExcelProperty("商铺ID")
    private Long shopId;

    @ExcelProperty("商铺名称")
    private String shopName;

    @ExcelProperty("评分周期")
    private String scorePeriod;

    @ExcelProperty("总分")
    private BigDecimal totalScore;

    @ExcelProperty("等级")
    private String shopLevel;

    @ExcelProperty("评分人")
    private String scoreUser;

    @ExcelProperty("评分时间")
    private LocalDateTime scoreTime;

    @ExcelProperty("评语")
    private String opinion;

    @ExcelProperty("创建时间")
    private LocalDateTime createTime;
}
