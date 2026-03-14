package com.ilbuy.common.core.result;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serial;
import java.io.Serializable;
import java.util.Collections;
import java.util.List;

/**
 * 分页响应结果封装
 *
 * <p>统一分页响应格式：
 * <pre>{@code
 * {
 *   "records": [...],
 *   "total": 100,
 *   "current": 1,
 *   "size": 10,
 *   "pages": 10,
 *   "hasNext": true,
 *   "hasPrev": false
 * }
 * }</pre>
 *
 * @param <T> 列表元素类型
 * @author ILbuy Team
 * @version 1.0.0
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "分页响应结果")
public class PageResult<T> implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    /** 数据列表 */
    @Schema(description = "数据列表")
    private List<T> records;

    /** 总记录数 */
    @Schema(description = "总记录数", example = "100")
    private long total;

    /** 当前页码（从1开始）*/
    @Schema(description = "当前页码", example = "1")
    private long current;

    /** 每页条数 */
    @Schema(description = "每页条数", example = "10")
    private long size;

    /** 总页数 */
    @Schema(description = "总页数", example = "10")
    private long pages;

    /** 是否有下一页 */
    @Schema(description = "是否有下一页")
    private boolean hasNext;

    /** 是否有上一页 */
    @Schema(description = "是否有上一页")
    private boolean hasPrev;

    /**
     * 构建分页结果
     *
     * @param records 数据列表
     * @param total   总记录数
     * @param current 当前页码
     * @param size    每页条数
     * @return 分页结果
     */
    public static <T> PageResult<T> of(List<T> records, long total, long current, long size) {
        long pages = size > 0 ? (total + size - 1) / size : 0;
        return PageResult.<T>builder()
                .records(records)
                .total(total)
                .current(current)
                .size(size)
                .pages(pages)
                .hasNext(current < pages)
                .hasPrev(current > 1)
                .build();
    }

    /**
     * 构建空分页结果
     *
     * @param current 当前页码
     * @param size    每页条数
     */
    public static <T> PageResult<T> empty(long current, long size) {
        return of(Collections.emptyList(), 0, current, size);
    }

    /**
     * 包装为Result
     */
    public Result<PageResult<T>> toResult() {
        return Result.ok(this);
    }
}
