package com.ilbuy.contract.model.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class SignContractRequest {

    @NotBlank(message = "签署方式不能为空")
    private String signMethod;

    private String signatureImageUrl;
}
