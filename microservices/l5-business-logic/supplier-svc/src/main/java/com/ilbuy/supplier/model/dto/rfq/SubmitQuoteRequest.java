package com.ilbuy.supplier.model.dto.rfq;

import jakarta.validation.constraints.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;

@Data
public class SubmitQuoteRequest {

    @NotNull(message = "单价不能为空")
    @DecimalMin(value = "0.00", inclusive = false, message = "单价必须大于0")
    private BigDecimal unitPrice;

    @NotNull(message = "预计交货天数不能为空")
    @Min(value = 1, message = "预计交货天数不能少于1天")
    private Integer deliveryDays;

    @NotNull(message = "报价有效期不能为空")
    @Future(message = "报价有效期必须是将来日期")
    private LocalDate validUntil;

    @NotBlank(message = "付款条件不能为空")
    private String paymentTerms;

    private String supplierRemark;
}
