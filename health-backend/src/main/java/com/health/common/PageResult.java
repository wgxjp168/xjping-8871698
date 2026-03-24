package com.health.common;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import lombok.Data;
import java.util.List;

/**
 * 分页响应结果
 */
@Data
public class PageResult<T> {

    private List<T> records;
    private Long total;
    private Long current;
    private Long size;
    private Long pages;

    public static <T> PageResult<T> of(Page<T> page) {
        PageResult<T> result = new PageResult<>();
        result.setRecords(page.getRecords());
        result.setTotal(page.getTotal());
        result.setCurrent(page.getCurrent());
        result.setSize(page.getSize());
        result.setPages(page.getPages());
        return result;
    }
}
