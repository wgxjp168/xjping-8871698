package com.ilbuy.common.core.enums;

import lombok.Getter;

/**
 * 会员等级枚举
 *
 * <p>商业变现层核心枚举：
 * <ul>
 *   <li>FREE - 免费用户：每月3次免费决策</li>
 *   <li>BASIC - 基础会员：每月30次决策，¥29/月</li>
 *   <li>PRO - 专业会员：不限次数，高级功能，¥99/月</li>
 *   <li>ENTERPRISE - 企业版：私有部署/API调用，定制报价</li>
 * </ul>
 *
 * @author ILbuy Team
 */
@Getter
public enum MemberLevelEnum {

    FREE("FREE", "免费用户", 3, 0),
    BASIC("BASIC", "基础会员", 30, 29),
    PRO("PRO", "专业会员", Integer.MAX_VALUE, 99),
    ENTERPRISE("ENTERPRISE", "企业版", Integer.MAX_VALUE, -1);

    /** 等级编码 */
    private final String code;

    /** 等级名称 */
    private final String name;

    /** 月度决策配额（-1表示按量计费）*/
    private final int monthlyQuota;

    /** 月费（元）*/
    private final int monthlyFee;

    MemberLevelEnum(String code, String name, int monthlyQuota, int monthlyFee) {
        this.code = code;
        this.name = name;
        this.monthlyQuota = monthlyQuota;
        this.monthlyFee = monthlyFee;
    }

    public static MemberLevelEnum fromCode(String code) {
        for (MemberLevelEnum level : values()) {
            if (level.code.equalsIgnoreCase(code)) {
                return level;
            }
        }
        return FREE;
    }

    /**
     * 判断是否有足够配额
     *
     * @param usedCount 已使用次数
     */
    public boolean hasQuota(int usedCount) {
        return this.monthlyQuota == Integer.MAX_VALUE || usedCount < this.monthlyQuota;
    }
}
