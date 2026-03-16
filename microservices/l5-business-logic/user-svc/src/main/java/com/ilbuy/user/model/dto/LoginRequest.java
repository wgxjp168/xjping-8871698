package com.ilbuy.user.model.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class LoginRequest {

    /** 支持用户名 / 邮箱 / 手机号 */
    @NotBlank
    private String principal;

    @NotBlank
    private String password;
}
