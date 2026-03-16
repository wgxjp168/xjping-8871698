package com.ilbuy.supplier.model.dto;

import com.ilbuy.supplier.model.enums.SupplierStatus;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class ChangeStatusRequest {

    @NotNull(message = "状态不能为空")
    private SupplierStatus status;
}
