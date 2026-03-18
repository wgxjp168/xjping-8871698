package com.ilbuy.common.core.enums;

import lombok.Getter;
import lombok.RequiredArgsConstructor;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.*;

@DisplayName("BaseEnum 业务枚举基接口测试")
class BaseEnumTest {

    /** 测试用枚举 */
    @Getter
    @RequiredArgsConstructor
    enum OrderStatus implements BaseEnum<Integer> {
        PENDING(0, "待支付"),
        PAID(1, "已支付"),
        CANCELLED(4, "已取消");

        private final Integer code;
        private final String description;
    }

    @Test
    @DisplayName("of - 根据 code 找到枚举")
    void of_found() {
        assertThat(BaseEnum.of(OrderStatus.class, 1)).isEqualTo(OrderStatus.PAID);
        assertThat(BaseEnum.of(OrderStatus.class, 0)).isEqualTo(OrderStatus.PENDING);
    }

    @Test
    @DisplayName("of - code 不存在返回 null")
    void of_notFound_returnsNull() {
        assertThat(BaseEnum.of(OrderStatus.class, 99)).isNull();
    }

    @Test
    @DisplayName("of - code 为 null 返回 null")
    void of_nullCode_returnsNull() {
        assertThat(BaseEnum.of(OrderStatus.class, null)).isNull();
    }

    @Test
    @DisplayName("ofRequired - 找到枚举正常返回")
    void ofRequired_found() {
        assertThat(BaseEnum.ofRequired(OrderStatus.class, 4)).isEqualTo(OrderStatus.CANCELLED);
    }

    @Test
    @DisplayName("ofRequired - 不存在抛 IllegalArgumentException")
    void ofRequired_notFound_throws() {
        assertThatThrownBy(() -> BaseEnum.ofRequired(OrderStatus.class, 99))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("OrderStatus");
    }

    @Test
    @DisplayName("contains - 存在返回 true")
    void contains_true() {
        assertThat(BaseEnum.contains(OrderStatus.class, 1)).isTrue();
    }

    @Test
    @DisplayName("contains - 不存在返回 false")
    void contains_false() {
        assertThat(BaseEnum.contains(OrderStatus.class, 99)).isFalse();
    }

    @Test
    @DisplayName("getDescription 返回正确文本")
    void getDescription_correct() {
        assertThat(OrderStatus.PAID.getDescription()).isEqualTo("已支付");
    }
}
