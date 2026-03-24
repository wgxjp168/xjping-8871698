package com.health.vo;

import lombok.Data;

/**
 * 登录响应
 */
@Data
public class LoginVO {

    private String token;
    private String tokenType = "Bearer";
    private Long userId;
    private String username;
    private String realName;
    private String role;
    private String avatar;
}
