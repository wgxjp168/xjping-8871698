package com.ilbuy.common.core.utils;

import com.ilbuy.common.core.constant.CommonConstants;
import org.apache.commons.lang3.StringUtils;

import java.util.regex.Pattern;

/**
 * 参数校验工具类
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
public final class ValidateUtils {

    private ValidateUtils() {}

    private static final Pattern PHONE_PATTERN = Pattern.compile(CommonConstants.REGEX_PHONE);
    private static final Pattern EMAIL_PATTERN = Pattern.compile(CommonConstants.REGEX_EMAIL);
    private static final Pattern CREDIT_CODE_PATTERN = Pattern.compile(CommonConstants.REGEX_CREDIT_CODE);
    private static final Pattern PASSWORD_PATTERN = Pattern.compile(CommonConstants.REGEX_PASSWORD);

    /**
     * 校验手机号（中国大陆）
     *
     * @param phone 手机号
     * @return 是否合法
     */
    public static boolean isPhone(String phone) {
        return StringUtils.isNotBlank(phone) && PHONE_PATTERN.matcher(phone).matches();
    }

    /**
     * 校验邮箱
     */
    public static boolean isEmail(String email) {
        return StringUtils.isNotBlank(email) && EMAIL_PATTERN.matcher(email).matches();
    }

    /**
     * 校验统一社会信用代码（B2B企业用户）
     */
    public static boolean isCreditCode(String creditCode) {
        return StringUtils.isNotBlank(creditCode) && CREDIT_CODE_PATTERN.matcher(creditCode).matches();
    }

    /**
     * 校验密码强度（8-20位，包含字母和数字）
     */
    public static boolean isStrongPassword(String password) {
        return StringUtils.isNotBlank(password) && PASSWORD_PATTERN.matcher(password).matches();
    }

    /**
     * 脱敏手机号（保留前3位和后4位）
     *
     * @param phone 原始手机号
     * @return 脱敏后的手机号，如：138****8888
     */
    public static String maskPhone(String phone) {
        if (!isPhone(phone)) {
            return phone;
        }
        return phone.substring(0, 3) + "****" + phone.substring(7);
    }

    /**
     * 脱敏邮箱（用户名保留前2位）
     *
     * @param email 原始邮箱
     * @return 脱敏后的邮箱，如：il****@example.com
     */
    public static String maskEmail(String email) {
        if (!isEmail(email)) {
            return email;
        }
        int atIndex = email.indexOf('@');
        String username = email.substring(0, atIndex);
        String domain = email.substring(atIndex);
        if (username.length() <= 2) {
            return username + "****" + domain;
        }
        return username.substring(0, 2) + "****" + domain;
    }

    /**
     * 脱敏统一社会信用代码（保留前4位和后4位）
     */
    public static String maskCreditCode(String creditCode) {
        if (StringUtils.isBlank(creditCode) || creditCode.length() < 8) {
            return creditCode;
        }
        return creditCode.substring(0, 4) + "**********" + creditCode.substring(14);
    }
}
