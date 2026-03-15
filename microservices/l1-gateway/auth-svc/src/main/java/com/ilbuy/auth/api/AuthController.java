package com.ilbuy.auth.api;

import com.ilbuy.auth.dto.LoginRequest;
import com.ilbuy.auth.dto.LoginResponse;
import com.ilbuy.auth.dto.TokenIntrospectResponse;
import com.ilbuy.auth.dto.TokenRefreshRequest;
import com.ilbuy.auth.service.AuthService;
import com.ilbuy.common.core.result.Result;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.web.bind.annotation.*;

/**
 * 认证授权 API 接口
 *
 * <p>数据流转：
 * <pre>
 *   L0 (WX/APP/H5)  →  api-gateway  →  POST /auth/login   →  返回 JWT
 *   L0 已认证请求    →  api-gateway  →  验证 JWT 黑名单   →  透传下游
 *   L1 gateway       →  POST /auth/introspect  →  验证 Token 详情
 * </pre>
 *
 * @author ILbuy Team
 */
@Slf4j
@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
@Tag(name = "认证授权接口", description = "登录/登出/刷新Token/Token自省")
public class AuthController {

    private final AuthService authService;

    /**
     * 用户登录
     */
    @PostMapping("/login")
    @Operation(summary = "用户登录", description = "账密登录，返回 AccessToken + RefreshToken")
    public Result<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        LoginResponse response = authService.login(request);
        return Result.ok(response);
    }

    /**
     * 刷新访问令牌
     */
    @PostMapping("/refresh")
    @Operation(summary = "刷新令牌", description = "使用 RefreshToken 换取新 AccessToken")
    public Result<LoginResponse> refresh(@Valid @RequestBody TokenRefreshRequest request) {
        LoginResponse response = authService.refresh(request);
        return Result.ok(response);
    }

    /**
     * 用户登出（主动吊销 Token）
     */
    @PostMapping("/logout")
    @Operation(summary = "用户登出", description = "将当前 AccessToken 加入黑名单")
    public Result<Void> logout(
            @RequestHeader(HttpHeaders.AUTHORIZATION) String authHeader) {
        String token = authHeader.startsWith("Bearer ")
            ? authHeader.substring(7) : authHeader;
        authService.logout(token);
        return Result.ok();
    }

    /**
     * Token 自省（网关/内部服务调用）
     */
    @PostMapping("/introspect")
    @Operation(summary = "Token自省", description = "验证 Token 有效性并返回用户信息（内部接口）")
    public Result<TokenIntrospectResponse> introspect(@RequestParam String token) {
        TokenIntrospectResponse response = authService.introspect(token);
        return Result.ok(response);
    }
}
