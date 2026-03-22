package com.ilbuy.supplier.dto;

import lombok.Data;

import javax.validation.constraints.Min;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Size;
import java.io.Serializable;
import java.time.LocalDateTime;

@Data
public class SupplierAbnormalDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    @NotNull(message = "供应商ID不能为空")
    private Long supplierId;

    @NotBlank(message = "异常类型不能为空")
    @Size(max = 50, message = "异常类型最多50字")
    private String abnType;

    @NotBlank(message = "异常内容不能为空")
    @Size(max = 500, message = "异常内容最多500字")
    private String abnContent;

    @NotNull(message = "异常时间不能为空")
    private LocalDateTime abnTime;

    @Min(value = 0, message = "扣分不能为负")
    private Integer deductionScore = 0;

    @Size(max = 200, message = "处理结果最多200字")
    private String handleResult;
}
