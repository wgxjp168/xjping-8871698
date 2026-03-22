package com.ilbuy.shop.vo;

import com.alibaba.excel.annotation.ExcelProperty;
import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
public class ShopInfoVO {

    @ExcelProperty("商铺ID")
    private Long shopId;

    @ExcelProperty("商铺名称")
    private String shopName;

    @ExcelProperty("类目名称")
    private String cateName;

    @ExcelProperty("联系人")
    private String contactUser;

    @ExcelProperty("联系电话")
    private String contactPhone;

    @ExcelProperty("状态")
    private String shopStatusName;

    @ExcelProperty("入驻时间")
    private LocalDate joinTime;

    @ExcelProperty("备注")
    private String remark;

    @ExcelProperty("创建时间")
    private LocalDateTime createTime;
}
