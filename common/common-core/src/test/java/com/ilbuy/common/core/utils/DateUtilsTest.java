package com.ilbuy.common.core.utils;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Date;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("DateUtils 日期工具测试")
class DateUtilsTest {

    @Test
    @DisplayName("formatDateTime 格式正确")
    void formatDateTime() {
        LocalDateTime ldt = LocalDateTime.of(2024, 6, 1, 12, 30, 59);
        assertThat(DateUtils.formatDateTime(ldt)).isEqualTo("2024-06-01 12:30:59");
    }

    @Test
    @DisplayName("parseDateTime 解析正确")
    void parseDateTime() {
        LocalDateTime parsed = DateUtils.parseDateTime("2024-06-01 12:30:59");
        assertThat(parsed.getYear()).isEqualTo(2024);
        assertThat(parsed.getMonthValue()).isEqualTo(6);
    }

    @Test
    @DisplayName("toDate / toLocalDateTime 互转")
    void convertBetweenDateAndLocalDateTime() {
        LocalDateTime original = LocalDateTime.of(2024, 1, 15, 10, 0, 0);
        Date date = DateUtils.toDate(original);
        LocalDateTime converted = DateUtils.toLocalDateTime(date);
        // 秒级比较（忽略纳秒）
        assertThat(converted.truncatedTo(java.time.temporal.ChronoUnit.SECONDS))
                .isEqualTo(original.truncatedTo(java.time.temporal.ChronoUnit.SECONDS));
    }

    @Test
    @DisplayName("daysBetween 天数差计算正确")
    void daysBetween() {
        LocalDate start = LocalDate.of(2024, 1, 1);
        LocalDate end   = LocalDate.of(2024, 1, 31);
        assertThat(DateUtils.daysBetween(start, end)).isEqualTo(30);
    }

    @Test
    @DisplayName("firstDayOfMonth / lastDayOfMonth 正确")
    void firstAndLastDay() {
        LocalDateTime dt = LocalDateTime.of(2024, 2, 15, 12, 0, 0);
        LocalDateTime first = DateUtils.firstDayOfMonth(dt);
        LocalDateTime last  = DateUtils.lastDayOfMonth(dt);
        assertThat(first.getDayOfMonth()).isEqualTo(1);
        assertThat(last.getDayOfMonth()).isEqualTo(29); // 2024 闰年
    }

    @Test
    @DisplayName("isBetween 边界判断")
    void isBetween() {
        LocalDateTime start  = LocalDateTime.of(2024, 1, 1, 0, 0, 0);
        LocalDateTime end    = LocalDateTime.of(2024, 12, 31, 23, 59, 59);
        LocalDateTime target = LocalDateTime.of(2024, 6, 15, 10, 0, 0);
        assertThat(DateUtils.isBetween(target, start, end)).isTrue();
        assertThat(DateUtils.isBetween(start, start, end)).isTrue(); // 包含边界
    }
}
