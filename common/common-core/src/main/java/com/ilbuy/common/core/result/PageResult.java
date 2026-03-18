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
 * 分页响应结果
 *
 * <pre>{@code
 * IPage<UserDO> page = userMapper.selectPage(new Page<>(pageNum, pageSize), wrapper);
 * return PageResult.of(page.getRecords(), page.getTotal(), pageNum, pageSize);
 * }</pre>
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "分页响应结果")
public class PageResult<T> implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Schema(description = "数据列表")
    private List<T> records;

    @Schema(description = "总记录数", example = "100")
    private long total;

    @Schema(description = "当前页码（从1开始）", example = "1")
    private long current;

    @Schema(description = "每页条数", example = "20")
    private long size;

    @Schema(description = "总页数", example = "5")
    private long pages;

    @Schema(description = "是否有上一页")
    private boolean hasPrevious;

    @Schema(description = "是否有下一页")
    private boolean hasNext;

    /**
     * 构建分页结果
     *
     * @param records  当页数据
     * @param total    总记录数
     * @param current  当前页
     * @param size     每页条数
     */
    public static <T> PageResult<T> of(List<T> records, long total, long current, long size) {
        if (records == null) {
            records = Collections.emptyList();
        }
        long pages = size > 0 ? (long) Math.ceil((double) total / size) : 0L;
        return PageResult.<T>builder()
                .records(records)
                .total(total)
                .current(current)
                .size(size)
                .pages(pages)
                .hasPrevious(current > 1)
                .hasNext(current < pages)
                .build();
    }

    /**
     * 空分页结果
     */
    public static <T> PageResult<T> empty(long current, long size) {
        return of(Collections.emptyList(), 0L, current, size);
    }

    /**
     * 包装为统一响应
     */
    public Result<PageResult<T>> toResult() {
        return Result.success(this);
    }
}
