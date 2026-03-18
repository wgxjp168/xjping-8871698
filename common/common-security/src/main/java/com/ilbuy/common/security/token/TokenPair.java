package com.ilbuy.common.security.token;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Builder;
import lombok.Data;

import java.io.Serial;
import java.io.Serializable;

/**
 * Token 对（Access Token + Refresh Token）
 *
 * <p>登录成功后返回给客户端，客户端需妥善保存：</p>
 * <ul>
 *   <li>accessToken  — 每次 API 请求携带于 Authorization: Bearer {token}</li>
 *   <li>refreshToken — Access 过期后调用 /auth/refresh 换取新的 Access Token</li>
 * </ul>
 *
 * <pre>{@code
 * // 生成
 * TokenPair pair = jwtTokenProvider.generateTokenPair(loginUser, ClientType.MOBILE);
 *
 * // 刷新
 * TokenPair newPair = jwtTokenProvider.refreshTokenPair(oldRefreshToken);
 * }</pre>
 */
@Data
@Builder
@Schema(description = "Token 对")
public class TokenPair implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Schema(description = "访问令牌")
    private String accessToken;

    @Schema(description = "刷新令牌")
    private String refreshToken;

    @Schema(description = "访问令牌有效期（秒）", example = "7200")
    private long accessExpire;

    @Schema(description = "刷新令牌有效期（秒）", example = "604800")
    private long refreshExpire;

    @Schema(description = "客户端类型", example = "web")
    private String clientType;
}
