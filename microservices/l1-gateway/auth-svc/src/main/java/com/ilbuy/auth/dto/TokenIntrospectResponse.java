package com.ilbuy.auth.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Builder;
import lombok.Data;

/**
 * Token 自省响应（网关内部调用，验证 Token 有效性并获取用户信息）
 */
@Data
@Builder
@Schema(description = "Token 自省响应")
public class TokenIntrospectResponse {

    @Schema(description = "Token 是否有效")
    private boolean active;

    @Schema(description = "用户ID")
    private String userId;

    @Schema(description = "用户类型")
    private String userType;

    @Schema(description = "角色")
    private String roles;

    @Schema(description = "过期时间（Unix 毫秒）")
    private long expiresAt;
}
