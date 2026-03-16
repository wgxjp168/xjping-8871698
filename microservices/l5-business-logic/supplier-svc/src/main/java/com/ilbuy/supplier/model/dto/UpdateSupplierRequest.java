package com.ilbuy.supplier.model.dto;

import jakarta.validation.constraints.Email;
import lombok.Data;

@Data
public class UpdateSupplierRequest {

    private String companyName;

    private String contactName;

    @Email(message = "联系邮箱格式不正确")
    private String contactEmail;

    private String contactPhone;
}
