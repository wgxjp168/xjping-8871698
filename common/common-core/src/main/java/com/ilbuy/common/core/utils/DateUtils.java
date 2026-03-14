package com.ilbuy.common.core.utils;

import java.time.*;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.Date;

/**
 * 日期时间工具类
 *
 * <p>基于Java 8 LocalDateTime，提供常用日期操作：
 * <ul>
 *   <li>格式化/解析</li>
 *   <li>时区转换</li>
 *   <li>时间计算（差值/加减）</li>
 *   <li>Date与LocalDateTime互转</li>
 * </ul>
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
public final class DateUtils {

    private DateUtils() {}

    // ==================== 常用格式化器 ====================
    public static final DateTimeFormatter FMT_DATETIME = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    public static final DateTimeFormatter FMT_DATE = DateTimeFormatter.ofPattern("yyyy-MM-dd");
    public static final DateTimeFormatter FMT_TIME = DateTimeFormatter.ofPattern("HH:mm:ss");
    public static final DateTimeFormatter FMT_COMPACT = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");
    public static final DateTimeFormatter FMT_MONTH = DateTimeFormatter.ofPattern("yyyy-MM");

    /** 系统时区 */
    public static final ZoneId ZONE_SHANGHAI = ZoneId.of("Asia/Shanghai");

    // ==================== 获取当前时间 ====================

    /**
     * 当前时间（LocalDateTime）
     */
    public static LocalDateTime now() {
        return LocalDateTime.now(ZONE_SHANGHAI);
    }

    /**
     * 当前日期（LocalDate）
     */
    public static LocalDate today() {
        return LocalDate.now(ZONE_SHANGHAI);
    }

    /**
     * 当前时间戳（毫秒）
     */
    public static long currentMillis() {
        return Instant.now().toEpochMilli();
    }

    // ==================== 格式化 ====================

    /**
     * LocalDateTime格式化为字符串（yyyy-MM-dd HH:mm:ss）
     */
    public static String format(LocalDateTime dateTime) {
        return dateTime == null ? null : dateTime.format(FMT_DATETIME);
    }

    /**
     * LocalDateTime格式化为指定格式
     */
    public static String format(LocalDateTime dateTime, DateTimeFormatter formatter) {
        return dateTime == null ? null : dateTime.format(formatter);
    }

    /**
     * LocalDate格式化（yyyy-MM-dd）
     */
    public static String format(LocalDate date) {
        return date == null ? null : date.format(FMT_DATE);
    }

    // ==================== 解析 ====================

    /**
     * 解析日期时间字符串（yyyy-MM-dd HH:mm:ss）
     */
    public static LocalDateTime parseDateTime(String str) {
        return str == null ? null : LocalDateTime.parse(str, FMT_DATETIME);
    }

    /**
     * 解析日期字符串（yyyy-MM-dd）
     */
    public static LocalDate parseDate(String str) {
        return str == null ? null : LocalDate.parse(str, FMT_DATE);
    }

    // ==================== 类型转换 ====================

    /**
     * Date转LocalDateTime
     */
    public static LocalDateTime toLocalDateTime(Date date) {
        return date == null ? null :
                date.toInstant().atZone(ZONE_SHANGHAI).toLocalDateTime();
    }

    /**
     * LocalDateTime转Date
     */
    public static Date toDate(LocalDateTime dateTime) {
        return dateTime == null ? null :
                Date.from(dateTime.atZone(ZONE_SHANGHAI).toInstant());
    }

    /**
     * 时间戳（毫秒）转LocalDateTime
     */
    public static LocalDateTime fromMillis(long millis) {
        return Instant.ofEpochMilli(millis).atZone(ZONE_SHANGHAI).toLocalDateTime();
    }

    /**
     * LocalDateTime转时间戳（毫秒）
     */
    public static long toMillis(LocalDateTime dateTime) {
        return dateTime.atZone(ZONE_SHANGHAI).toInstant().toEpochMilli();
    }

    // ==================== 时间计算 ====================

    /**
     * 计算两个时间相差的天数
     */
    public static long daysBetween(LocalDate start, LocalDate end) {
        return ChronoUnit.DAYS.between(start, end);
    }

    /**
     * 计算两个时间相差的小时数
     */
    public static long hoursBetween(LocalDateTime start, LocalDateTime end) {
        return ChronoUnit.HOURS.between(start, end);
    }

    /**
     * 计算两个时间相差的分钟数
     */
    public static long minutesBetween(LocalDateTime start, LocalDateTime end) {
        return ChronoUnit.MINUTES.between(start, end);
    }

    /**
     * 获取当前月份的第一天（含时分秒：00:00:00）
     */
    public static LocalDateTime firstDayOfMonth() {
        return today().withDayOfMonth(1).atStartOfDay();
    }

    /**
     * 获取当前月份的最后一天（含时分秒：23:59:59）
     */
    public static LocalDateTime lastDayOfMonth() {
        LocalDate lastDay = today().withDayOfMonth(today().lengthOfMonth());
        return lastDay.atTime(23, 59, 59);
    }

    /**
     * 判断指定时间是否已过期
     *
     * @param expireTime 过期时间
     */
    public static boolean isExpired(LocalDateTime expireTime) {
        return expireTime != null && LocalDateTime.now(ZONE_SHANGHAI).isAfter(expireTime);
    }

    /**
     * 生成订单号（时间戳+随机4位）
     * 格式：yyyyMMddHHmmss + 4位随机数
     */
    public static String generateOrderNo() {
        return now().format(FMT_COMPACT) +
                String.format("%04d", (int) (Math.random() * 10000));
    }
}
