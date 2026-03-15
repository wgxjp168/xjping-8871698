package com.ilbuy.auth.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Builder;
import lombok.Data;

/**
 * 登录响应 DTO
 */
@Data
@Builder
@Schema(description = "登录响应")
public class LoginResponse {

    @Schema(description = "访问令牌（JWT）")
    private String accessToken;

    @Schema(description = "刷新令牌")
    private String refreshToken;

    @Schema(description = "令牌类型", example = "Bearer")
    private String tokenType;

    @Schema(description = "访问令牌有效期（秒）", example = "7200")
    private long expiresIn;

    @Schema(description = "用户ID", example = "10001")
    private String userId;

    @Schema(description = "用户类型：BUSINESS / CONSUMER", example = "CONSUMER")
    private String userType;

    @Schema(description = "角色列表", example = "ROLE_USER")
    private String roles;
}
