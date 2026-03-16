package com.ilbuy.supplier.model.dto.rfq;

import jakarta.validation.constraints.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;

@Data
public class CreateRfqRequest {

    @NotBlank(message = "供应商编号不能为空")
    private String supplierNo;

    @NotBlank(message = "商品描述不能为空")
    private String productDescription;

    private String canonicalId;

    @NotNull(message = "数量不能为空")
    @Min(value = 1, message = "数量不能少于1")
    private Integer quantity;

    @NotBlank(message = "单位不能为空")
    private String unit;

    @NotNull(message = "要求交货日期不能为空")
    @Future(message = "要求交货日期必须是将来日期")
    private LocalDate requiredDeliveryDate;

    @NotBlank(message = "交货地址不能为空")
    private String deliveryAddress;

    @DecimalMin(value = "0.00", inclusive = false, message = "预算金额必须大于0")
    private BigDecimal budgetAmount;

    private String buyerRemark;
}
