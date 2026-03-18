package com.ilbuy.common.core.result;

import com.ilbuy.common.core.enums.ResultCode;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("Result 统一响应测试")
class ResultTest {

    @Test
    @DisplayName("success() 返回 200 且无数据")
    void success_noData() {
        Result<Void> result = Result.success();
        assertThat(result.getCode()).isEqualTo(200);
        assertThat(result.isSuccess()).isTrue();
        assertThat(result.getData()).isNull();
    }

    @Test
    @DisplayName("success(data) 携带数据")
    void success_withData() {
        String data   = "hello";
        Result<String> result = Result.success(data);
        assertThat(result.isSuccess()).isTrue();
        assertThat(result.getData()).isEqualTo(data);
    }

    @Test
    @DisplayName("fail(ResultCode) 返回对应 code/message")
    void fail_withResultCode() {
        Result<Void> result = Result.fail(ResultCode.NOT_FOUND);
        assertThat(result.getCode()).isEqualTo(404);
        assertThat(result.isFail()).isTrue();
        assertThat(result.getMessage()).isEqualTo(ResultCode.NOT_FOUND.getMessage());
    }

    @Test
    @DisplayName("fail(ResultCode, customMsg) 覆盖 message")
    void fail_customMessage() {
        Result<Void> result = Result.fail(ResultCode.BIZ_ERROR, "订单 123 不存在");
        assertThat(result.getCode()).isEqualTo(ResultCode.BIZ_ERROR.getCode());
        assertThat(result.getMessage()).isEqualTo("订单 123 不存在");
    }

    @Test
    @DisplayName("timestamp 非空")
    void timestamp_notNull() {
        Result<Void> result = Result.success();
        assertThat(result.getTimestamp()).isPositive();
    }

    @Test
    @DisplayName("traceId 链式设置")
    void traceId_chain() {
        Result<Void> result = Result.success().traceId("abc-123");
        assertThat(result.getTraceId()).isEqualTo("abc-123");
    }

    @Test
    @DisplayName("PageResult.of 分页计算正确")
    void pageResult_of() {
        List<String> records = List.of("a", "b", "c");
        PageResult<String> page = PageResult.of(records, 100L, 2L, 20L);
        assertThat(page.getTotal()).isEqualTo(100);
        assertThat(page.getPages()).isEqualTo(5);
        assertThat(page.isHasPrevious()).isTrue();
        assertThat(page.isHasNext()).isTrue();
        assertThat(page.getRecords()).hasSize(3);
    }

    @Test
    @DisplayName("PageResult.empty 返回空集合")
    void pageResult_empty() {
        PageResult<String> page = PageResult.empty(1L, 20L);
        assertThat(page.getRecords()).isEmpty();
        assertThat(page.getTotal()).isZero();
        assertThat(page.isHasPrevious()).isFalse();
        assertThat(page.isHasNext()).isFalse();
    }
}
