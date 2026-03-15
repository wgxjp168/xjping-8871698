package com.ilbuy.auth.service.impl;

import com.ilbuy.auth.config.JwtProperties;
import com.ilbuy.auth.dto.LoginRequest;
import com.ilbuy.auth.dto.LoginResponse;
import com.ilbuy.auth.dto.TokenIntrospectResponse;
import com.ilbuy.auth.dto.TokenRefreshRequest;
import com.ilbuy.auth.entity.UserCredential;
import com.ilbuy.auth.mapper.UserCredentialMapper;
import com.ilbuy.auth.service.AuthService;
import com.ilbuy.auth.util.JwtUtils;
import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.common.core.result.ResultCode;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.Duration;

/**
 * 认证授权服务实现
 *
 * <p>核心流程：
 * <ol>
 *   <li>login: 查数据库 → BCrypt 验密 → 签发双 Token → RefreshToken 写 Redis</li>
 *   <li>refresh: 验 RefreshToken 签名 → Redis 存在校验 → 签发新 AccessToken</li>
 *   <li>logout: AccessToken jti 写 Redis 黑名单</li>
 *   <li>introspect: 解析 Token → 查黑名单 → 返回用户信息</li>
 * </ol>
 *
 * @author ILbuy Team
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AuthServiceImpl implements AuthService {

    private final UserCredentialMapper credentialMapper;
    private final JwtUtils jwtUtils;
    private final JwtProperties jwtProperties;
    private final PasswordEncoder passwordEncoder;
    private final StringRedisTemplate redisTemplate;

    @Override
    public LoginResponse login(LoginRequest request) {
        // 1. 查找用户凭证
        UserCredential credential = credentialMapper.findByLoginId(request.getLoginId());
        if (credential == null) {
            throw new BizException(ResultCode.USER_NOT_FOUND);
        }

        // 2. 账号状态校验
        if (credential.getEnabled() != null && credential.getEnabled() == 0) {
            throw new BizException(ResultCode.USER_DISABLED);
        }

        // 3. 密码校验
        if (!passwordEncoder.matches(request.getPassword(), credential.getPasswordHash())) {
            throw new BizException(ResultCode.USER_PASSWORD_ERROR);
        }

        String userId = credential.getUserId().toString();
        String userType = credential.getUserType();
        String roles = credential.getRoles() != null ? credential.getRoles() : "ROLE_USER";

        // 4. 签发双 Token
        String accessToken = jwtUtils.generateAccessToken(userId, userType, roles);
        String refreshToken = jwtUtils.generateRefreshToken(userId);

        // 5. RefreshToken 存入 Redis（支持主动吊销）
        String refreshKey = jwtProperties.getRefreshKeyPrefix() + userId;
        redisTemplate.opsForValue().set(refreshKey, refreshToken,
            Duration.ofSeconds(jwtProperties.getRefreshTokenTtl()));

        log.info("[登录成功] userId={} userType={}", userId, userType);

        return LoginResponse.builder()
            .accessToken(accessToken)
            .refreshToken(refreshToken)
            .tokenType("Bearer")
            .expiresIn(jwtProperties.getAccessTokenTtl())
            .userId(userId)
            .userType(userType)
            .roles(roles)
            .build();
    }

    @Override
    public LoginResponse refresh(TokenRefreshRequest request) {
        String refreshToken = request.getRefreshToken();

        // 1. 验证 RefreshToken 签名与有效期
        Claims claims;
        try {
            claims = jwtUtils.parseToken(refreshToken);
        } catch (ExpiredJwtException e) {
            throw new BizException(ResultCode.REFRESH_TOKEN_EXPIRED);
        } catch (JwtException e) {
            throw new BizException(ResultCode.TOKEN_INVALID);
        }

        // 2. 校验 Token 类型
        String type = claims.get("type", String.class);
        if (!"refresh".equals(type)) {
            throw new BizException(ResultCode.TOKEN_INVALID);
        }

        String userId = claims.getSubject();

        // 3. Redis 中校验 RefreshToken 是否有效（防止多设备重放）
        String refreshKey = jwtProperties.getRefreshKeyPrefix() + userId;
        String storedToken = redisTemplate.opsForValue().get(refreshKey);
        if (storedToken == null || !storedToken.equals(refreshToken)) {
            throw new BizException(ResultCode.TOKEN_INVALID);
        }

        // 4. 查询用户凭证（获取最新角色信息）
        UserCredential credential = credentialMapper.findByLoginId(userId);
        if (credential == null || (credential.getEnabled() != null && credential.getEnabled() == 0)) {
            throw new BizException(ResultCode.USER_DISABLED);
        }

        String userType = credential.getUserType();
        String roles = credential.getRoles() != null ? credential.getRoles() : "ROLE_USER";

        // 5. 签发新 AccessToken（RefreshToken 不轮换，减少客户端复杂度）
        String newAccessToken = jwtUtils.generateAccessToken(userId, userType, roles);

        log.info("[Token刷新] userId={}", userId);

        return LoginResponse.builder()
            .accessToken(newAccessToken)
            .refreshToken(refreshToken)
            .tokenType("Bearer")
            .expiresIn(jwtProperties.getAccessTokenTtl())
            .userId(userId)
            .userType(userType)
            .roles(roles)
            .build();
    }

    @Override
    public void logout(String accessToken) {
        Claims claims = jwtUtils.parseTokenQuietly(accessToken);
        if (claims == null) {
            return; // Token 已过期或无效，无需操作
        }

        String jti = claims.getId();
        long remainingMillis = claims.getExpiration().getTime() - System.currentTimeMillis();

        if (remainingMillis > 0) {
            // 将 jti 写入黑名单，TTL = Token 剩余有效期
            String blacklistKey = jwtProperties.getBlacklistKeyPrefix() + jti;
            redisTemplate.opsForValue().set(blacklistKey, "1",
                Duration.ofMillis(remainingMillis));
        }

        // 删除 RefreshToken
        String userId = claims.getSubject();
        redisTemplate.delete(jwtProperties.getRefreshKeyPrefix() + userId);

        log.info("[登出] userId={} jti={}", userId, jti);
    }

    @Override
    public TokenIntrospectResponse introspect(String token) {
        Claims claims = jwtUtils.parseTokenQuietly(token);
        if (claims == null) {
            return TokenIntrospectResponse.builder().active(false).build();
        }

        // 检查黑名单
        String jti = claims.getId();
        Boolean isBlacklisted = redisTemplate.hasKey(jwtProperties.getBlacklistKeyPrefix() + jti);
        if (Boolean.TRUE.equals(isBlacklisted)) {
            return TokenIntrospectResponse.builder().active(false).build();
        }

        return TokenIntrospectResponse.builder()
            .active(true)
            .userId(claims.getSubject())
            .userType(claims.get("userType", String.class))
            .roles(claims.get("roles", String.class))
            .expiresAt(claims.getExpiration().getTime())
            .build();
    }
}
