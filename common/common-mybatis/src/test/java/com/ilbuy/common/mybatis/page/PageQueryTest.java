package com.ilbuy.common.mybatis.page;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.ilbuy.common.core.result.PageResult;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * PageQuery 单元测试
 *
 * @author ILbuy Team
 */
@DisplayName("PageQuery 测试")
class PageQueryTest {

    // ================================================================
    //  toPage 转换
    // ================================================================

    @Nested
    @DisplayName("toPage() 分页对象转换")
    class ToPageTests {

        @Test
        @DisplayName("默认参数（page=1, size=10）转换正确")
        void toPage_defaultValues() {
            PageQuery query = new PageQuery();
            IPage<Object> page = query.toPage();

            assertThat(page.getCurrent()).isEqualTo(1L);
            assertThat(page.getSize()).isEqualTo(10L);
        }

        @Test
        @DisplayName("自定义页码和每页条数转换正确")
        void toPage_customValues() {
            PageQuery query = new PageQuery();
            query.setCurrent(3);
            query.setSize(50);
            IPage<Object> page = query.toPage();

            assertThat(page.getCurrent()).isEqualTo(3L);
            assertThat(page.getSize()).isEqualTo(50L);
        }

        @Test
        @DisplayName("最大每页条数 100 可正常转换")
        void toPage_maxSize() {
            PageQuery query = new PageQuery();
            query.setCurrent(1);
            query.setSize(100);
            IPage<Object> page = query.toPage();

            assertThat(page.getSize()).isEqualTo(100L);
        }
    }

    // ================================================================
    //  toPageResult 结果转换
    // ================================================================

    @Nested
    @DisplayName("toPageResult() 结果封装")
    class ToPageResultTests {

        @Test
        @DisplayName("带 mapper 转换：实体列表正确映射")
        void toPageResult_withMapper() {
            Page<String> page = new Page<>(2, 5);
            page.setTotal(15);
            page.setRecords(List.of("a", "b", "c"));

            PageResult<Integer> result = PageQuery.toPageResult(page, String::length);

            assertThat(result.getRecords()).containsExactly(1, 1, 1);
            assertThat(result.getTotal()).isEqualTo(15L);
            assertThat(result.getCurrent()).isEqualTo(2L);
            assertThat(result.getSize()).isEqualTo(5L);
        }

        @Test
        @DisplayName("不带 mapper 转换：直接封装同类型列表")
        void toPageResult_withoutMapper() {
            Page<String> page = new Page<>(1, 10);
            page.setTotal(3);
            page.setRecords(List.of("x", "y", "z"));

            PageResult<String> result = PageQuery.toPageResult(page);

            assertThat(result.getRecords()).containsExactly("x", "y", "z");
            assertThat(result.getTotal()).isEqualTo(3L);
        }

        @Test
        @DisplayName("空记录列表转换正常")
        void toPageResult_emptyRecords() {
            Page<String> page = new Page<>(1, 10);
            page.setTotal(0);
            page.setRecords(List.of());

            PageResult<String> result = PageQuery.toPageResult(page);

            assertThat(result.getRecords()).isEmpty();
            assertThat(result.getTotal()).isEqualTo(0L);
        }
    }

    // ================================================================
    //  默认值和排序字段
    // ================================================================

    @Nested
    @DisplayName("默认值与属性")
    class DefaultValueTests {

        @Test
        @DisplayName("默认排序方向为 desc")
        void defaultOrderDirection_isDesc() {
            PageQuery query = new PageQuery();
            assertThat(query.getOrderDirection()).isEqualTo("desc");
        }

        @Test
        @DisplayName("排序字段默认为 null")
        void defaultOrderBy_isNull() {
            PageQuery query = new PageQuery();
            assertThat(query.getOrderBy()).isNull();
        }

        @Test
        @DisplayName("可设置自定义排序字段")
        void setOrderBy_customField() {
            PageQuery query = new PageQuery();
            query.setOrderBy("createTime");
            query.setOrderDirection("asc");

            assertThat(query.getOrderBy()).isEqualTo("createTime");
            assertThat(query.getOrderDirection()).isEqualTo("asc");
        }
    }
}
