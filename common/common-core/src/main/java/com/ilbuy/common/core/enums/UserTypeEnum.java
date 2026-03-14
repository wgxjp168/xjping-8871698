package com.ilbuy.common.core.enums;

import lombok.Getter;

/**
 * 用户类型枚举
 *
 * <p>ILbuy平台支持两类用户：
 * <ul>
 *   <li>B2B - 企业采购：关注供应商资质、批量价格、认证资质</li>
 *   <li>B2C - 个人消费：关注性价比、品质、口碑</li>
 * </ul>
 *
 * @author ILbuy Team
 */
@Getter
public enum UserTypeEnum {

    /** B2B企业采购用户 */
    B2B("B2B", "企业采购"),

    /** B2C个人消费用户 */
    B2C("B2C", "个人消费");

    /** 类型编码 */
    private final String code;

    /** 类型名称 */
    private final String name;

    UserTypeEnum(String code, String name) {
        this.code = code;
        this.name = name;
    }

    /**
     * 根据code获取枚举
     *
     * @param code 类型编码
     * @return UserTypeEnum
     */
    public static UserTypeEnum fromCode(String code) {
        for (UserTypeEnum type : values()) {
            if (type.code.equalsIgnoreCase(code)) {
                return type;
            }
        }
        throw new IllegalArgumentException("未知用户类型: " + code);
    }
}
