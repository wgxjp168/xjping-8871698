package com.ilbuy.shop.common;

import com.github.pagehelper.PageInfo;
import lombok.Data;

import java.util.List;

/**
 * 分页响应封装
 */
@Data
public class PageResult<T> {

    /** 当前页 */
    private int pageNum;
    /** 每页条数 */
    private int pageSize;
    /** 总条数 */
    private long total;
    /** 总页数 */
    private int pages;
    /** 数据列表 */
    private List<T> list;

    /**
     * 从 PageHelper 的 PageInfo 构建
     */
    public static <T> PageResult<T> of(PageInfo<T> pageInfo) {
        PageResult<T> r = new PageResult<>();
        r.pageNum  = pageInfo.getPageNum();
        r.pageSize = pageInfo.getPageSize();
        r.total    = pageInfo.getTotal();
        r.pages    = pageInfo.getPages();
        r.list     = pageInfo.getList();
        return r;
    }

    public static <T> PageResult<T> of(List<T> list, long total, int pageNum, int pageSize) {
        PageResult<T> r = new PageResult<>();
        r.list     = list;
        r.total    = total;
        r.pageNum  = pageNum;
        r.pageSize = pageSize;
        r.pages    = (int) Math.ceil((double) total / pageSize);
        return r;
    }
}
