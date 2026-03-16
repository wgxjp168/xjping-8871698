package com.ilbuy.supplier.model.dto;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.math.BigDecimal;

@Data
public class AddScoreRequest {

    @NotNull(message = "订单ID不能为空")
    private Long orderId;

    @NotNull(message = "质量评分不能为空")
    @DecimalMin(value = "0.0", message = "评分不能小于0")
    @DecimalMax(value = "10.0", message = "评分不能大于10")
    private BigDecimal qualityScore;

    @NotNull(message = "交付评分不能为空")
    @DecimalMin(value = "0.0", message = "评分不能小于0")
    @DecimalMax(value = "10.0", message = "评分不能大于10")
    private BigDecimal deliveryScore;

    @NotNull(message = "服务评分不能为空")
    @DecimalMin(value = "0.0", message = "评分不能小于0")
    @DecimalMax(value = "10.0", message = "评分不能大于10")
    private BigDecimal serviceScore;

    private String comment;
}
