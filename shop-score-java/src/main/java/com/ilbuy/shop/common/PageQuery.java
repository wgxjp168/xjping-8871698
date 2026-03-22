package com.ilbuy.shop.common;

import lombok.Data;

import javax.validation.constraints.Max;
import javax.validation.constraints.Min;

/**
 * 通用分页查询基类
 */
@Data
public class PageQuery {

    @Min(value = 1, message = "页码最小为1")
    private int pageNum = 1;

    @Min(value = 1, message = "每页条数最小为1")
    @Max(value = 200, message = "每页条数最大200")
    private int pageSize = 20;
}
