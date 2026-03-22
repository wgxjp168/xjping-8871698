package com.ilbuy.shop.constant;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;

public class ShopScoreConstants {

    // ---------- 评分项类型 ----------
    public static final int SCORE_COMPLIANCE = 1;  // 商品合规 25分
    public static final int SCORE_SERVICE    = 2;  // 服务     20分
    public static final int SCORE_DELIVERY   = 3;  // 履约     20分
    public static final int SCORE_QUALITY    = 4;  // 品质     25分
    public static final int SCORE_COOPERATE  = 5;  // 配合      5分
    public static final int SCORE_VIOLATION  = 6;  // 违规      5分

    // ---------- 各项满分 ----------
    public static final Integer SCORE_FULL_COMPLIANCE = 25;
    public static final Integer SCORE_FULL_SERVICE    = 20;
    public static final Integer SCORE_FULL_DELIVERY   = 20;
    public static final Integer SCORE_FULL_QUALITY    = 25;
    public static final Integer SCORE_FULL_COOPERATE  =  5;
    public static final Integer SCORE_FULL_VIOLATION  =  5;

    // ---------- 满分 MAP（key=scoreRule） ----------
    public static final Map<Integer, BigDecimal> FULL_SCORE_MAP = new HashMap<>();
    static {
        FULL_SCORE_MAP.put(SCORE_COMPLIANCE, new BigDecimal("25"));
        FULL_SCORE_MAP.put(SCORE_SERVICE,    new BigDecimal("20"));
        FULL_SCORE_MAP.put(SCORE_DELIVERY,   new BigDecimal("20"));
        FULL_SCORE_MAP.put(SCORE_QUALITY,    new BigDecimal("25"));
        FULL_SCORE_MAP.put(SCORE_COOPERATE,  new BigDecimal("5"));
        FULL_SCORE_MAP.put(SCORE_VIOLATION,  new BigDecimal("5"));
    }

    // ---------- 评分项名称 MAP ----------
    public static final Map<Integer, String> SCORE_RULE_NAME_MAP = new HashMap<>();
    static {
        SCORE_RULE_NAME_MAP.put(SCORE_COMPLIANCE, "商品合规");
        SCORE_RULE_NAME_MAP.put(SCORE_SERVICE,    "服务");
        SCORE_RULE_NAME_MAP.put(SCORE_DELIVERY,   "履约");
        SCORE_RULE_NAME_MAP.put(SCORE_QUALITY,    "品质");
        SCORE_RULE_NAME_MAP.put(SCORE_COOPERATE,  "配合");
        SCORE_RULE_NAME_MAP.put(SCORE_VIOLATION,  "违规");
    }

    // ---------- 等级阈值 ----------
    public static final int LEVEL_A_MIN = 90;
    public static final int LEVEL_B_MIN = 80;
    public static final int LEVEL_C_MIN = 70;

    // ---------- 商铺状态 ----------
    public static final int SHOP_STATUS_NORMAL  = 1;  // 正常
    public static final int SHOP_STATUS_SUSPEND = 2;  // 暂停
    public static final int SHOP_STATUS_CLOSED  = 3;  // 关闭

    // ---------- 类目状态 ----------
    public static final int CATE_STATUS_ON  = 1;  // 启用
    public static final int CATE_STATUS_OFF = 0;  // 禁用

    private ShopScoreConstants() {}
}
