package com.health.physical.common.dto;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Result统一响应对象测试
 */
@DisplayName("Result - 统一响应体测试")
class ResultTest {

    @Test
    @DisplayName("ok()返回200且data为null")
    void ok_noData() {
        Result<Void> result = Result.ok();
        assertEquals(200, result.getCode());
        assertEquals("操作成功", result.getMessage());
        assertNull(result.getData());
        assertTrue(result.isOk());
        assertNotNull(result.getTimestamp());
    }

    @Test
    @DisplayName("ok(data)返回200且data正确")
    void ok_withData() {
        Result<String> result = Result.ok("hello");
        assertEquals(200, result.getCode());
        assertEquals("hello", result.getData());
        assertTrue(result.isOk());
    }

    @Test
    @DisplayName("ok(message,data)自定义消息")
    void ok_withMessageAndData() {
        Result<Integer> result = Result.ok("新增成功", 42);
        assertEquals(200, result.getCode());
        assertEquals("新增成功", result.getMessage());
        assertEquals(42, result.getData());
    }

    @Test
    @DisplayName("fail(message)返回500")
    void fail_message() {
        Result<Void> result = Result.fail("操作失败");
        assertEquals(500, result.getCode());
        assertEquals("操作失败", result.getMessage());
        assertFalse(result.isOk());
    }

    @Test
    @DisplayName("fail(code,message)自定义状态码")
    void fail_codeAndMessage() {
        Result<Void> result = Result.fail(400, "参数错误");
        assertEquals(400, result.getCode());
        assertEquals("参数错误", result.getMessage());
        assertFalse(result.isOk());
    }

    @Test
    @DisplayName("unauthorized返回401")
    void unauthorized() {
        Result<Void> result = Result.unauthorized("未登录");
        assertEquals(401, result.getCode());
        assertFalse(result.isOk());
    }

    @Test
    @DisplayName("forbidden返回403")
    void forbidden() {
        Result<Void> result = Result.forbidden("无权限");
        assertEquals(403, result.getCode());
        assertFalse(result.isOk());
    }
}
