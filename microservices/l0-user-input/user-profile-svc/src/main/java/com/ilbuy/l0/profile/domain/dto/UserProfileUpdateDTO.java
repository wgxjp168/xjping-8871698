package com.ilbuy.l0.profile.domain.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

/**
 * 用户画像更新请求 DTO
 *
 * <p>所有字段均为可选，仅更新传入的字段（PATCH语义）。
 *
 * @author ILbuy Team
 */
@Data
@Schema(description = "用户画像更新请求")
public class UserProfileUpdateDTO {

    @Schema(description = "性别（0未知/1男/2女）")
    @Min(0) @Max(2)
    private Integer gender;

    @Schema(description = "年龄段", example = "25-35")
    private String ageGroup;

    @Schema(description = "城市（省-市）", example = "广东-深圳")
    @Size(max = 50)
    private String city;

    @Schema(description = "预算下限（元）", example = "1000")
    @DecimalMin("0")
    private BigDecimal budgetMin;

    @Schema(description = "预算上限（元）", example = "5000")
    @DecimalMin("0")
    private BigDecimal budgetMax;

    @Schema(description = "偏好品类（覆盖式更新）", example = "[\"手机\",\"电脑\"]")
    @Size(max = 20)
    private List<String> preferredCategories;

    @Schema(description = "购物场景标签（覆盖式更新）", example = "[\"自用\",\"礼物\"]")
    @Size(max = 10)
    private List<String> sceneTags;

    @Schema(description = "偏好品牌（覆盖式更新）", example = "[\"华为\",\"苹果\"]")
    @Size(max = 30)
    private List<String> preferredBrands;

    @Schema(description = "偏好电商平台（覆盖式更新）", example = "[\"jd\",\"taobao\"]")
    @Size(max = 7)
    private List<String> preferredPlatforms;

    @Schema(description = "是否关注环保")
    private Boolean ecoFriendly;
}
