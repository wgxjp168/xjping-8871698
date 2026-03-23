package com.huidong.physical.common.utils;

import cn.hutool.core.util.IdUtil;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * ID生成工具类
 */
public class IdUtils {

    private static final DateTimeFormatter DATE_FMT = DateTimeFormatter.ofPattern("yyyyMMdd");

    private IdUtils() {}

    /**
     * 生成体检单号：PE + 日期 + 6位雪花尾号
     */
    public static String generateExamNo() {
        String date = LocalDateTime.now().format(DATE_FMT);
        String suffix = String.valueOf(IdUtil.getSnowflakeNextId()).substring(8, 14);
        return "PE" + date + suffix;
    }

    /**
     * 生成标本编号：SP + 日期 + 6位雪花尾号
     */
    public static String generateSpecimenNo() {
        String date = LocalDateTime.now().format(DATE_FMT);
        String suffix = String.valueOf(IdUtil.getSnowflakeNextId()).substring(8, 14);
        return "SP" + date + suffix;
    }

    /**
     * 生成雪花ID
     */
    public static Long nextId() {
        return IdUtil.getSnowflakeNextId();
    }
}
