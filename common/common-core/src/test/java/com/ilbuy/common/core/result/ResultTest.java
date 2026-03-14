package com.ilbuy.common.core.result;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Result 响应结果单元测试
 *
 * @author ILbuy Team
 */
@DisplayName("Result 统一响应测试")
class ResultTest {

    @Test
    @DisplayName("ok() 无数据成功响应")
    void testOkNoData() {
        Result<Void> result = Result.ok();
        assertThat(result.getCode()).isEqualTo(200);
        assertThat(result.getMessage()).isEqualTo("操作成功");
        assertThat(result.getData()).isNull();
        assertThat(result.isSuccess()).isTrue();
        assertThat(result.isFail()).isFalse();
        assertThat(result.getTimestamp()).isPositive();
    }

    @Test
    @DisplayName("ok(data) 携带数据成功响应")
    void testOkWithData() {
        String data = "测试数据";
        Result<String> result = Result.ok(data);
        assertThat(result.getCode()).isEqualTo(200);
        assertThat(result.getData()).isEqualTo(data);
        assertThat(result.isSuccess()).isTrue();
    }

    @Test
    @DisplayName("fail(ResultCode) 使用枚举失败响应")
    void testFailWithResultCode() {
        Result<Void> result = Result.fail(ResultCode.USER_NOT_FOUND);
        assertThat(result.getCode()).isEqualTo(1001);
        assertThat(result.getMessage()).isEqualTo("用户不存在");
        assertThat(result.isSuccess()).isFalse();
        assertThat(result.isFail()).isTrue();
    }

    @Test
    @DisplayName("fail(code, message) 自定义失败响应")
    void testFailWithCustomCodeAndMessage() {
        Result<Void> result = Result.fail(9999, "自定义错误");
        assertThat(result.getCode()).isEqualTo(9999);
        assertThat(result.getMessage()).isEqualTo("自定义错误");
    }

    @Test
    @DisplayName("badRequest() 参数错误响应")
    void testBadRequest() {
        Result<Void> result = Result.badRequest("手机号格式错误");
        assertThat(result.getCode()).isEqualTo(400);
        assertThat(result.getMessage()).isEqualTo("手机号格式错误");
    }

    @Test
    @DisplayName("unauthorized() 未授权响应")
    void testUnauthorized() {
        Result<Void> result = Result.unauthorized();
        assertThat(result.getCode()).isEqualTo(401);
    }

    @Test
    @DisplayName("tooManyRequests() 限流响应")
    void testTooManyRequests() {
        Result<Void> result = Result.tooManyRequests();
        assertThat(result.getCode()).isEqualTo(429);
    }
}
