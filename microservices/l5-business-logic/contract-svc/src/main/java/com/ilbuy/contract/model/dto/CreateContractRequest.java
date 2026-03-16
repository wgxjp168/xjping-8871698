package com.ilbuy.contract.model.dto;

import com.ilbuy.contract.model.enums.ContractType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;

@Data
public class CreateContractRequest {

    @NotNull(message = "订单ID不能为空")
    private Long orderId;

    @NotBlank(message = "供应商编号不能为空")
    private String supplierNo;

    @NotBlank(message = "合同标题不能为空")
    private String title;

    @NotNull(message = "合同类型不能为空")
    private ContractType type;

    @NotNull(message = "合同金额不能为空")
    @Positive(message = "合同金额必须大于0")
    private BigDecimal totalAmount;

    private LocalDate expiresAt;
}
