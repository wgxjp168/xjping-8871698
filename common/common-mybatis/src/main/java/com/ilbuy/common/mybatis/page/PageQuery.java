package com.ilbuy.common.mybatis.page;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.ilbuy.common.core.constant.CommonConstants;
import com.ilbuy.common.core.result.PageResult;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.Data;

import java.util.List;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * 分页查询基础参数
 *
 * <p>所有分页查询接口的请求参数基类，使用示例：
 * <pre>{@code
 * // Controller中直接接收
 * public Result<PageResult<UserVO>> list(PageQuery query) {
 *     IPage<User> page = userService.page(query.toPage(), lambdaQuery);
 *     return Result.ok(PageQuery.toPageResult(page, UserVO::from));
 * }
 * }</pre>
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@Data
@Schema(description = "分页查询参数")
public class PageQuery {

    /**
     * 当前页码（从1开始）
     */
    @Schema(description = "页码，从1开始", example = "1")
    @Min(value = 1, message = "页码最小为1")
    private int current = CommonConstants.DEFAULT_PAGE_NUM;

    /**
     * 每页条数（默认10，最大100）
     */
    @Schema(description = "每页条数，最大100", example = "10")
    @Min(value = 1, message = "每页条数最小为1")
    @Max(value = 100, message = "每页条数最大为100")
    private int size = CommonConstants.DEFAULT_PAGE_SIZE;

    /**
     * 排序字段（需校验，防止SQL注入）
     */
    @Schema(description = "排序字段", example = "createTime")
    private String orderBy;

    /**
     * 排序方向：asc/desc
     */
    @Schema(description = "排序方向：asc/desc", example = "desc")
    private String orderDirection = "desc";

    /**
     * 转换为 MyBatis-Plus IPage 对象
     *
     * @param <T> 实体类型
     * @return IPage
     */
    public <T> IPage<T> toPage() {
        return new Page<>(current, size);
    }

    /**
     * 将 MyBatis-Plus IPage 结果转换为 PageResult
     *
     * @param page   MyBatis-Plus分页结果
     * @param mapper 实体转VO的转换函数
     * @param <E>    实体类型
     * @param <V>    VO类型
     * @return PageResult
     */
    public static <E, V> PageResult<V> toPageResult(IPage<E> page, Function<E, V> mapper) {
        List<V> records = page.getRecords()
                .stream()
                .map(mapper)
                .collect(Collectors.toList());
        return PageResult.of(records, page.getTotal(), page.getCurrent(), page.getSize());
    }

    /**
     * 直接将 MyBatis-Plus IPage 结果转换为 PageResult（不转换类型）
     *
     * @param page MyBatis-Plus分页结果
     * @param <T>  类型
     */
    public static <T> PageResult<T> toPageResult(IPage<T> page) {
        return PageResult.of(page.getRecords(), page.getTotal(), page.getCurrent(), page.getSize());
    }
}
