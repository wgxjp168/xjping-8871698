package com.ilbuy.shop.vo;

import com.alibaba.excel.annotation.ExcelProperty;
import lombok.Data;
import java.time.LocalDateTime;

@Data
public class ShopOperateLogVO {

    @ExcelProperty("日志ID")
    private Long id;

    @ExcelProperty("商铺ID")
    private Long shopId;

    @ExcelProperty("商铺名称")
    private String shopName;

    @ExcelProperty("操作类型")
    private String operateType;

    @ExcelProperty("操作内容")
    private String operateContent;

    @ExcelProperty("操作人")
    private String operateUser;

    @ExcelProperty("操作时间")
    private LocalDateTime operateTime;
}
