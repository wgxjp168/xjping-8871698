package com.ilbuy.common.core.utils;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("StringUtils 字符串工具测试")
class StringUtilsTest {

    // ──────── 空值判断 ────────

    @Test
    @DisplayName("isBlank: null/空/空白返回 true")
    void isBlank_trueForNullOrWhitespace() {
        assertThat(StringUtils.isBlank(null)).isTrue();
        assertThat(StringUtils.isBlank("")).isTrue();
        assertThat(StringUtils.isBlank("   ")).isTrue();
    }

    @Test
    @DisplayName("isBlank: 非空返回 false")
    void isBlank_falseForContent() {
        assertThat(StringUtils.isBlank("hello")).isFalse();
    }

    @Test
    @DisplayName("defaultIfBlank: blank 时返回默认值")
    void defaultIfBlank_returnsDefault() {
        assertThat(StringUtils.defaultIfBlank(null, "default")).isEqualTo("default");
        assertThat(StringUtils.defaultIfBlank("  ", "default")).isEqualTo("default");
        assertThat(StringUtils.defaultIfBlank("value", "default")).isEqualTo("value");
    }

    // ──────── 手机号校验 ────────

    @ParameterizedTest(name = "valid mobile: {0}")
    @ValueSource(strings = {"13812345678", "15900000000", "18699999999", "+8613812345678"})
    @DisplayName("isMobile: 合法手机号返回 true")
    void isMobile_valid(String mobile) {
        assertThat(StringUtils.isMobile(mobile)).isTrue();
    }

    @ParameterizedTest(name = "invalid mobile: {0}")
    @ValueSource(strings = {"12345678901", "1381234567", "23812345678", "abcdefghijk"})
    @DisplayName("isMobile: 非法手机号返回 false")
    void isMobile_invalid(String mobile) {
        assertThat(StringUtils.isMobile(mobile)).isFalse();
    }

    // ──────── 邮箱校验 ────────

    @ParameterizedTest(name = "valid email: {0}")
    @ValueSource(strings = {"user@example.com", "test.name+tag@sub.domain.cn"})
    @DisplayName("isEmail: 合法邮箱返回 true")
    void isEmail_valid(String email) {
        assertThat(StringUtils.isEmail(email)).isTrue();
    }

    @ParameterizedTest(name = "invalid email: {0}")
    @ValueSource(strings = {"notanemail", "@nodomain", "missing@", "spaces in@email.com"})
    @DisplayName("isEmail: 非法邮箱返回 false")
    void isEmail_invalid(String email) {
        assertThat(StringUtils.isEmail(email)).isFalse();
    }

    // ──────── 命名格式转换 ────────

    @ParameterizedTest(name = "{0} → {1}")
    @CsvSource({"userName,user_name", "userId,user_id", "createTime,create_time", "id,id"})
    @DisplayName("toSnakeCase 驼峰转下划线")
    void toSnakeCase(String input, String expected) {
        assertThat(StringUtils.toSnakeCase(input)).isEqualTo(expected);
    }

    @ParameterizedTest(name = "{0} → {1}")
    @CsvSource({"user_name,userName", "user_id,userId", "create_time,createTime", "id,id"})
    @DisplayName("toCamelCase 下划线转驼峰")
    void toCamelCase(String input, String expected) {
        assertThat(StringUtils.toCamelCase(input)).isEqualTo(expected);
    }

    // ──────── 脱敏 ────────

    @Test
    @DisplayName("maskMobile 手机号脱敏")
    void maskMobile_correct() {
        assertThat(StringUtils.maskMobile("13812345678")).isEqualTo("138****5678");
    }

    @Test
    @DisplayName("maskEmail 邮箱脱敏")
    void maskEmail_correct() {
        assertThat(StringUtils.maskEmail("user@example.com")).isEqualTo("u***@example.com");
    }

    @Test
    @DisplayName("truncate 超长截断并加省略号")
    void truncate_addsEllipsis() {
        assertThat(StringUtils.truncate("Hello World", 5)).isEqualTo("Hello...");
        assertThat(StringUtils.truncate("Hi", 5)).isEqualTo("Hi");
    }
}
