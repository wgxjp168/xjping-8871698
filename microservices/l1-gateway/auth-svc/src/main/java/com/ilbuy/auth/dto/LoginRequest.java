package com.ilbuy.auth.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 登录请求 DTO
 */
@Data
@Schema(description = "登录请求")
public class LoginRequest {

    @NotBlank(message = "登录账号不能为空")
    @Schema(description = "登录账号（用户名/手机号/邮箱）", example = "user@example.com")
    private String loginId;

    @NotBlank(message = "密码不能为空")
    @Schema(description = "登录密码", example = "P@ssword123")
    private String password;

    @Schema(description = "客户端类型：WEB / APP / MINI_PROGRAM", example = "WEB")
    private String clientType = "WEB";
}
