package com.ilbuy.l0.profile.domain.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.Builder;

import java.math.BigDecimal;
import java.util.List;

/**
 * 用户画像视图对象（对外返回）
 *
 * <p>整合 UserProfile + UserPreference，
 * 供 L0 输入解析和 L1/L2 决策引擎消费。
 *
 * @author ILbuy Team
 */
@Data
@Builder
@Schema(description = "用户画像视图")
public class UserProfileVO {

    @Schema(description = "用户ID")
    private Long userId;

    @Schema(description = "昵称")
    private String nickname;

    @Schema(description = "性别（0未知/1男/2女）")
    private Integer gender;

    @Schema(description = "年龄段", example = "25-35")
    private String ageGroup;

    @Schema(description = "城市")
    private String city;

    // ===== 预算信息 =====
    @Schema(description = "用户设置的最低预算（元）")
    private BigDecimal budgetMin;

    @Schema(description = "用户设置的最高预算（元）")
    private BigDecimal budgetMax;

    @Schema(description = "历史平均消费下限（系统计算）")
    private BigDecimal avgSpendMin;

    @Schema(description = "历史平均消费上限（系统计算）")
    private BigDecimal avgSpendMax;

    // ===== 偏好信息 =====
    @Schema(description = "偏好品类列表", example = "[\"手机\",\"电脑\",\"耳机\"]")
    private List<String> preferredCategories;

    @Schema(description = "购物场景标签", example = "[\"自用\",\"礼物\"]")
    private List<String> sceneTags;

    @Schema(description = "偏好品牌", example = "[\"华为\",\"苹果\"]")
    private List<String> preferredBrands;

    @Schema(description = "偏好电商平台", example = "[\"jd\",\"taobao\"]")
    private List<String> preferredPlatforms;

    // ===== 摘要 =====
    @Schema(description = "画像完整度（0-100）")
    private Integer profileScore;

    @Schema(description = "购物频次（low/medium/high）")
    private String purchaseFrequency;

    @Schema(description = "偏好明细列表（细粒度）")
    private List<PreferenceItem> preferences;

    @Data
    @Builder
    @Schema(description = "偏好明细")
    public static class PreferenceItem {
        @Schema(description = "维度（category/brand/platform/scene）")
        private String dimension;
        @Schema(description = "维度值")
        private String dimensionValue;
        @Schema(description = "偏好权重（1-100）")
        private Integer weight;
        @Schema(description = "来源（manual/inferred）")
        private String source;
    }
}
