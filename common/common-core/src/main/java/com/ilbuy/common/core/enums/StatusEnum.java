package com.ilbuy.common.core.enums;

import lombok.Getter;

/**
 * 通用状态枚举
 *
 * @author ILbuy Team
 */
@Getter
public enum StatusEnum {

    /** 正常/启用 */
    ENABLED(1, "正常"),

    /** 禁用 */
    DISABLED(0, "禁用");

    private final int code;
    private final String name;

    StatusEnum(int code, String name) {
        this.code = code;
        this.name = name;
    }

    public static StatusEnum fromCode(int code) {
        for (StatusEnum status : values()) {
            if (status.code == code) {
                return status;
            }
        }
        throw new IllegalArgumentException("未知状态码: " + code);
    }

    public boolean isEnabled() {
        return this == ENABLED;
    }
}
