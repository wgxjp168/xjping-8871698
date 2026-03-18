package com.ilbuy.common.core.utils;

import com.ilbuy.common.core.constants.CommonConstants;

import java.util.Collection;
import java.util.regex.Pattern;

/**
 * 字符串工具类（扩展 Spring StringUtils，补充业务校验）
 */
public final class StringUtils extends org.springframework.util.StringUtils {

    private StringUtils() {}

    private static final Pattern MOBILE_PATTERN  = Pattern.compile(CommonConstants.REGEX_MOBILE);
    private static final Pattern EMAIL_PATTERN   = Pattern.compile(CommonConstants.REGEX_EMAIL);
    private static final Pattern ID_CARD_PATTERN = Pattern.compile(CommonConstants.REGEX_ID_CARD);

    // ──────────────────── 空值判断 ────────────────────

    public static boolean isBlank(String str) {
        return str == null || str.isBlank();
    }

    public static boolean isNotBlank(String str) {
        return !isBlank(str);
    }

    public static boolean isEmpty(Collection<?> coll) {
        return coll == null || coll.isEmpty();
    }

    public static boolean isNotEmpty(Collection<?> coll) {
        return !isEmpty(coll);
    }

    /** 若 str 为 null 或空白返回 defaultVal */
    public static String defaultIfBlank(String str, String defaultVal) {
        return isBlank(str) ? defaultVal : str;
    }

    // ──────────────────── 业务格式校验 ────────────────────

    /** 校验手机号（支持 +86 前缀自动忽略） */
    public static boolean isMobile(String mobile) {
        if (isBlank(mobile)) return false;
        String cleaned = mobile.startsWith("+86") ? mobile.substring(3) : mobile;
        cleaned = cleaned.replaceAll("\\s|-", "");
        return MOBILE_PATTERN.matcher(cleaned).matches();
    }

    /** 校验邮箱地址 */
    public static boolean isEmail(String email) {
        if (isBlank(email)) return false;
        return EMAIL_PATTERN.matcher(email.trim()).matches();
    }

    /** 校验身份证号（18位，含校验位） */
    public static boolean isIdCard(String idCard) {
        if (isBlank(idCard)) return false;
        if (!ID_CARD_PATTERN.matcher(idCard).matches()) return false;
        return validateIdCardChecksum(idCard);
    }

    // ──────────────────── 字符串操作 ────────────────────

    /** 驼峰转下划线：userInfo → user_info */
    public static String toSnakeCase(String camelCase) {
        if (isBlank(camelCase)) return camelCase;
        return camelCase.replaceAll("([A-Z])", "_$1").toLowerCase()
                .replaceAll("^_", "");
    }

    /** 下划线转小驼峰：user_info → userInfo */
    public static String toCamelCase(String snakeCase) {
        if (isBlank(snakeCase)) return snakeCase;
        StringBuilder sb = new StringBuilder();
        boolean nextUpper = false;
        for (char c : snakeCase.toCharArray()) {
            if (c == '_') {
                nextUpper = true;
            } else {
                sb.append(nextUpper ? Character.toUpperCase(c) : c);
                nextUpper = false;
            }
        }
        return sb.toString();
    }

    /** 手机号脱敏：13812345678 → 138****5678 */
    public static String maskMobile(String mobile) {
        if (!isMobile(mobile)) return mobile;
        return mobile.substring(0, 3) + "****" + mobile.substring(7);
    }

    /** 邮箱脱敏：user@example.com → u***@example.com */
    public static String maskEmail(String email) {
        if (!isEmail(email)) return email;
        int atIdx = email.indexOf('@');
        String local  = email.substring(0, atIdx);
        String domain = email.substring(atIdx);
        String masked = local.length() <= 1 ? local : local.charAt(0) + "***";
        return masked + domain;
    }

    /** 身份证脱敏：441234199001011234 → 441234****01011234 */
    public static String maskIdCard(String idCard) {
        if (isBlank(idCard) || idCard.length() < 10) return idCard;
        return idCard.substring(0, 6) + "****" + idCard.substring(idCard.length() - 4);
    }

    /** 截断字符串（超长则追加省略号） */
    public static String truncate(String str, int maxLength) {
        if (isBlank(str) || str.length() <= maxLength) return str;
        return str.substring(0, maxLength) + "...";
    }

    // ──────────────────── 私有：身份证校验位 ────────────────────

    private static boolean validateIdCardChecksum(String idCard) {
        int[] weights = {7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2};
        char[] checks = {'1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2'};
        int sum = 0;
        for (int i = 0; i < 17; i++) {
            char c = idCard.charAt(i);
            if (!Character.isDigit(c)) return false;
            sum += (c - '0') * weights[i];
        }
        char expected = checks[sum % 11];
        return Character.toUpperCase(idCard.charAt(17)) == expected;
    }
}
