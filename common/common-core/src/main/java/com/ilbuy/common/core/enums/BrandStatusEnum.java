package com.ilbuy.common.core.enums;

import lombok.Getter;

/**
 * 品牌状态枚举
 *
 * <p>用于区分用户采购决策中对品牌的态度：
 * <ul>
 *   <li>DECIDED - 已定品牌：用户指定了特定品牌，重点评估正品渠道/服务</li>
 *   <li>UNDECIDED - 未定品牌：用户未指定品牌，重点评估参数匹配和综合性价比</li>
 * </ul>
 *
 * @author ILbuy Team
 */
@Getter
public enum BrandStatusEnum {

    /** 已确定品牌 */
    DECIDED("decided", "已定品牌"),

    /** 未确定品牌 */
    UNDECIDED("undecided", "未定品牌");

    private final String code;
    private final String name;

    BrandStatusEnum(String code, String name) {
        this.code = code;
        this.name = name;
    }

    public static BrandStatusEnum fromCode(String code) {
        for (BrandStatusEnum status : values()) {
            if (status.code.equalsIgnoreCase(code)) {
                return status;
            }
        }
        throw new IllegalArgumentException("未知品牌状态: " + code);
    }
}
