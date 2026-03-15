package com.ilbuy.l0.profile.domain.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import lombok.experimental.Accessors;

import java.time.LocalDateTime;

/**
 * 用户偏好明细实体
 *
 * <p>对应数据库表 {@code user_preference}，
 * 记录用户对特定品类/品牌/价格段的偏好程度（细粒度）。
 * 一个用户可有多条偏好记录（按品类维度）。
 *
 * @author ILbuy Team
 */
@Data
@Accessors(chain = true)
@TableName("user_preference")
public class UserPreference {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 用户ID（关联 user_profile.user_id）*/
    private Long userId;

    /** 偏好维度：category / brand / platform / scene */
    private String dimension;

    /** 维度值（如 "手机", "华为", "jd", "礼物"）*/
    private String dimensionValue;

    /** 偏好权重（1-100，越高越偏好）*/
    private Integer weight;

    /** 来源：manual（用户设置）/ inferred（行为推断）*/
    private String source;

    /** 最近触发时间（行为推断时更新）*/
    private LocalDateTime lastTriggeredAt;

    /** 触发次数（行为计数）*/
    private Integer triggerCount;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;

    @TableLogic
    private Integer deleted;
}
