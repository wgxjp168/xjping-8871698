package com.ilbuy.auth.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 刷新令牌请求 DTO
 */
@Data
@Schema(description = "令牌刷新请求")
public class TokenRefreshRequest {

    @NotBlank(message = "refreshToken 不能为空")
    @Schema(description = "刷新令牌")
    private String refreshToken;
}
