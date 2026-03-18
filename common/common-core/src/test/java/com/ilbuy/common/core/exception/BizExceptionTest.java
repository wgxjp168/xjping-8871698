package com.ilbuy.common.core.exception;

import com.ilbuy.common.core.enums.ResultCode;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.*;

@DisplayName("BizException 业务异常测试")
class BizExceptionTest {

    @Test
    @DisplayName("ResultCode 构造 — code/message 匹配")
    void construct_byResultCode() {
        BizException ex = new BizException(ResultCode.USER_NOT_FOUND);
        assertThat(ex.getCode()).isEqualTo(ResultCode.USER_NOT_FOUND.getCode());
        assertThat(ex.getMessage()).isEqualTo(ResultCode.USER_NOT_FOUND.getMessage());
    }

    @Test
    @DisplayName("自定义消息覆盖")
    void construct_customMessage() {
        BizException ex = new BizException(ResultCode.BIZ_ERROR, "订单 99 不存在");
        assertThat(ex.getMessage()).isEqualTo("订单 99 不存在");
    }

    @Test
    @DisplayName("格式化消息 {}")
    void construct_formattedMessage() {
        BizException ex = new BizException(ResultCode.BIZ_ERROR, "用户 {} 已存在", "zhangsan");
        assertThat(ex.getMessage()).contains("zhangsan");
    }

    @Test
    @DisplayName("notNull 断言 — obj 为 null 时抛出")
    void notNull_throwsWhenNull() {
        assertThatThrownBy(() -> BizException.notNull(null, ResultCode.DATA_NOT_EXIST))
                .isInstanceOf(BizException.class)
                .hasMessageContaining(ResultCode.DATA_NOT_EXIST.getMessage());
    }

    @Test
    @DisplayName("notNull 断言 — obj 非 null 时不抛出")
    void notNull_passesWhenNotNull() {
        assertThatNoException().isThrownBy(() -> BizException.notNull("value", ResultCode.DATA_NOT_EXIST));
    }

    @Test
    @DisplayName("isTrue 断言 — false 时抛出")
    void isTrue_throwsWhenFalse() {
        assertThatThrownBy(() -> BizException.isTrue(false, ResultCode.FORBIDDEN))
                .isInstanceOf(BizException.class);
    }

    @Test
    @DisplayName("不记录堆栈信息（性能优化）")
    void noStackTrace() {
        BizException ex = new BizException(ResultCode.BIZ_ERROR);
        assertThat(ex.getStackTrace()).isEmpty();
    }
}
