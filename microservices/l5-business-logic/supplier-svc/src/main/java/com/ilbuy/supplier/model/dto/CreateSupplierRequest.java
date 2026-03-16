package com.ilbuy.supplier.model.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CreateSupplierRequest {

    @NotBlank(message = "公司名称不能为空")
    private String companyName;

    @NotBlank(message = "联系人姓名不能为空")
    private String contactName;

    @NotBlank(message = "联系邮箱不能为空")
    @Email(message = "联系邮箱格式不正确")
    private String contactEmail;

    private String contactPhone;

    @NotBlank(message = "营业执照号不能为空")
    private String businessLicense;
}
