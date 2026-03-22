package com.ilbuy.supplier.constant;

import java.math.BigDecimal;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class SupplierScoreConstant {

    private SupplierScoreConstant() {
    }

    /** 评分类型：产品质量 */
    public static final int TYPE_QUALITY = 1;
    /** 评分类型：交付能力 */
    public static final int TYPE_DELIVERY = 2;
    /** 评分类型：价格成本 */
    public static final int TYPE_COST = 3;
    /** 评分类型：资质合规 */
    public static final int TYPE_RULE = 4;
    /** 评分类型：售后服务 */
    public static final int TYPE_SERVICE = 5;
    /** 评分类型：合作稳定 */
    public static final int TYPE_STABLE = 6;

    /** 各评分类型满分 */
    public static final Map<Integer, BigDecimal> FULL_SCORE;

    static {
        Map<Integer, BigDecimal> map = new HashMap<>();
        map.put(TYPE_QUALITY, new BigDecimal("30"));
        map.put(TYPE_DELIVERY, new BigDecimal("25"));
        map.put(TYPE_COST, new BigDecimal("20"));
        map.put(TYPE_RULE, new BigDecimal("10"));
        map.put(TYPE_SERVICE, new BigDecimal("10"));
        map.put(TYPE_STABLE, new BigDecimal("5"));
        FULL_SCORE = Collections.unmodifiableMap(map);
    }

    /** 各评分类型名称 */
    public static final Map<Integer, String> TYPE_NAME_MAP;

    static {
        Map<Integer, String> map = new HashMap<>();
        map.put(TYPE_QUALITY, "产品质量");
        map.put(TYPE_DELIVERY, "交付能力");
        map.put(TYPE_COST, "价格成本");
        map.put(TYPE_RULE, "资质合规");
        map.put(TYPE_SERVICE, "售后服务");
        map.put(TYPE_STABLE, "合作稳定");
        TYPE_NAME_MAP = Collections.unmodifiableMap(map);
    }

    /** 供应商状态：正常 */
    public static final int SUPPLIER_STATUS_NORMAL = 1;
    /** 供应商状态：暂停 */
    public static final int SUPPLIER_STATUS_SUSPEND = 2;
    /** 供应商状态：关闭 */
    public static final int SUPPLIER_STATUS_CLOSED = 3;

    /** 分类状态：启用 */
    public static final int CATE_STATUS_ON = 1;
    /** 分类状态：禁用 */
    public static final int CATE_STATUS_OFF = 0;

    /**
     * 根据总分获取等级
     * A>=90, B>=80, C>=70, else D
     */
    public static String getLevel(BigDecimal total) {
        if (total == null) {
            return "D";
        }
        if (total.compareTo(new BigDecimal("90")) >= 0) {
            return "A";
        } else if (total.compareTo(new BigDecimal("80")) >= 0) {
            return "B";
        } else if (total.compareTo(new BigDecimal("70")) >= 0) {
            return "C";
        } else {
            return "D";
        }
    }
}
