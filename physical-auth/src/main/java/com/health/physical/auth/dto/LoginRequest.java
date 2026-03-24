package com.health.physical.auth.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;

/**
 * 登录请求DTO
 */
@Data
public class LoginRequest {

    @NotBlank(message = "用户名不能为空")
    private String username;

    @NotBlank(message = "密码不能为空")
    private String password;

    /** 客户端MAC地址（网页端传入，用于绑定校验） */
    private String macAddress;

    /** 登录来源：WEB-网页端，APP-移动端，PAD-平板 */
    private String loginSource;
}
