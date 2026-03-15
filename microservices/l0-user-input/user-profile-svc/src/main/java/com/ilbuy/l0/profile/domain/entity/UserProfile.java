package com.ilbuy.l0.profile.domain.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import lombok.experimental.Accessors;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 用户画像实体
 *
 * <p>对应数据库表 {@code user_profile}，存储用户级别的购物画像信息。
 * 每个用户唯一一条记录，随行为数据增量更新。
 *
 * <p>预算字段说明：
 * <ul>
 *   <li>{@code budgetMin/Max} - 用户主动设置的预算区间</li>
 *   <li>{@code avgSpendMin/Max} - 系统根据历史订单计算的消费区间（只读）</li>
 * </ul>
 *
 * @author ILbuy Team
 */
@Data
@Accessors(chain = true)
@TableName("user_profile")
public class UserProfile {

    @TableId(type = IdType.INPUT)
    private Long userId;

    /** 昵称（冗余，减少联表） */
    private String nickname;

    /** 性别：0-未知 1-男 2-女 */
    private Integer gender;

    /** 年龄段：18-25, 25-35, 35-45, 45+ */
    private String ageGroup;

    /** 所在城市（省-市） */
    private String city;

    /** 用户主动设置的最低预算（元） */
    private BigDecimal budgetMin;

    /** 用户主动设置的最高预算（元） */
    private BigDecimal budgetMax;

    /** 历史平均消费下限（系统计算） */
    private BigDecimal avgSpendMin;

    /** 历史平均消费上限（系统计算） */
    private BigDecimal avgSpendMax;

    /** 偏好品类（逗号分隔，如 "手机,电脑,耳机"） */
    private String preferredCategories;

    /** 购物场景标签（逗号分隔，如 "自用,礼物,商务"） */
    private String sceneTags;

    /** 偏好品牌（逗号分隔） */
    private String preferredBrands;

    /** 偏好电商平台（逗号分隔，如 "jd,taobao"） */
    private String preferredPlatforms;

    /** 购物频次：low/medium/high */
    private String purchaseFrequency;

    /** 是否关注环保/可持续 */
    private Boolean ecoFriendly;

    /** 画像完整度分（0-100） */
    private Integer profileScore;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;

    @Version
    private Integer version;

    @TableLogic
    private Integer deleted;
}
