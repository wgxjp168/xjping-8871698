package com.ilbuy.auth.service;

import com.ilbuy.auth.dto.LoginRequest;
import com.ilbuy.auth.dto.LoginResponse;
import com.ilbuy.auth.dto.TokenIntrospectResponse;
import com.ilbuy.auth.dto.TokenRefreshRequest;

/**
 * 认证授权服务接口
 */
public interface AuthService {

    /**
     * 用户登录（账密认证，返回双 Token）
     *
     * @param request 登录请求
     * @return 含 accessToken + refreshToken 的登录响应
     */
    LoginResponse login(LoginRequest request);

    /**
     * 刷新访问令牌
     *
     * @param request 含 refreshToken 的刷新请求
     * @return 新的登录响应（含新 accessToken，refreshToken 复用或轮换）
     */
    LoginResponse refresh(TokenRefreshRequest request);

    /**
     * 登出（将 accessToken 加入黑名单）
     *
     * @param accessToken 待吊销的访问令牌（不含 Bearer 前缀）
     */
    void logout(String accessToken);

    /**
     * Token 自省（网关或内部服务验证 Token 并获取用户信息）
     *
     * @param token 访问令牌
     * @return Token 自省响应
     */
    TokenIntrospectResponse introspect(String token);
}
