package com.ilbuy.common.core.utils;

import com.ilbuy.common.core.constants.CommonConstants;

import java.time.*;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.time.temporal.TemporalAdjusters;
import java.util.Date;

/**
 * 日期工具类（基于 Java 8 Time API，线程安全）
 */
public final class DateUtils {

    private DateUtils() {}

    public static final ZoneId ZONE_SHANGHAI = ZoneId.of("Asia/Shanghai");

    private static final DateTimeFormatter FMT_DATETIME = DateTimeFormatter.ofPattern(CommonConstants.DATETIME_FORMAT);
    private static final DateTimeFormatter FMT_DATE     = DateTimeFormatter.ofPattern(CommonConstants.DATE_FORMAT);
    private static final DateTimeFormatter FMT_TIME     = DateTimeFormatter.ofPattern(CommonConstants.TIME_FORMAT);

    // ──────────────────── 获取当前时间 ────────────────────

    public static LocalDateTime now() {
        return LocalDateTime.now(ZONE_SHANGHAI);
    }

    public static LocalDate today() {
        return LocalDate.now(ZONE_SHANGHAI);
    }

    public static long currentTimestamp() {
        return Instant.now().toEpochMilli();
    }

    // ──────────────────── 格式化 ────────────────────

    public static String formatDateTime(LocalDateTime dateTime) {
        if (dateTime == null) return null;
        return dateTime.format(FMT_DATETIME);
    }

    public static String formatDate(LocalDate date) {
        if (date == null) return null;
        return date.format(FMT_DATE);
    }

    public static String formatTime(LocalTime time) {
        if (time == null) return null;
        return time.format(FMT_TIME);
    }

    public static String format(LocalDateTime dateTime, String pattern) {
        if (dateTime == null) return null;
        return dateTime.format(DateTimeFormatter.ofPattern(pattern));
    }

    // ──────────────────── 解析 ────────────────────

    public static LocalDateTime parseDateTime(String dateStr) {
        if (dateStr == null || dateStr.isBlank()) return null;
        return LocalDateTime.parse(dateStr, FMT_DATETIME);
    }

    public static LocalDate parseDate(String dateStr) {
        if (dateStr == null || dateStr.isBlank()) return null;
        return LocalDate.parse(dateStr, FMT_DATE);
    }

    // ──────────────────── 转换 ────────────────────

    public static Date toDate(LocalDateTime ldt) {
        if (ldt == null) return null;
        return Date.from(ldt.atZone(ZONE_SHANGHAI).toInstant());
    }

    public static LocalDateTime toLocalDateTime(Date date) {
        if (date == null) return null;
        return date.toInstant().atZone(ZONE_SHANGHAI).toLocalDateTime();
    }

    public static LocalDateTime toLocalDateTime(long epochMilli) {
        return Instant.ofEpochMilli(epochMilli).atZone(ZONE_SHANGHAI).toLocalDateTime();
    }

    public static long toEpochMilli(LocalDateTime ldt) {
        return ldt.atZone(ZONE_SHANGHAI).toInstant().toEpochMilli();
    }

    // ──────────────────── 计算 ────────────────────

    /**
     * 两个日期之间的天数差（end - start）
     */
    public static long daysBetween(LocalDate start, LocalDate end) {
        return ChronoUnit.DAYS.between(start, end);
    }

    /**
     * 两个时间之间的秒数差
     */
    public static long secondsBetween(LocalDateTime start, LocalDateTime end) {
        return ChronoUnit.SECONDS.between(start, end);
    }

    /**
     * 获取当月第一天 00:00:00
     */
    public static LocalDateTime firstDayOfMonth(LocalDateTime ldt) {
        return ldt.with(TemporalAdjusters.firstDayOfMonth()).withHour(0).withMinute(0).withSecond(0).withNano(0);
    }

    /**
     * 获取当月最后一天 23:59:59
     */
    public static LocalDateTime lastDayOfMonth(LocalDateTime ldt) {
        return ldt.with(TemporalAdjusters.lastDayOfMonth()).withHour(23).withMinute(59).withSecond(59).withNano(0);
    }

    /**
     * 判断是否在时间范围内（包含边界）
     */
    public static boolean isBetween(LocalDateTime target, LocalDateTime start, LocalDateTime end) {
        return !target.isBefore(start) && !target.isAfter(end);
    }

    /**
     * 是否今天
     */
    public static boolean isToday(LocalDate date) {
        return today().equals(date);
    }
}
