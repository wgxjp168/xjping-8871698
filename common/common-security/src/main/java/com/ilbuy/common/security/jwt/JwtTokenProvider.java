package com.ilbuy.common.security.jwt;

import com.ilbuy.common.core.constants.CommonConstants;
import com.ilbuy.common.security.model.LoginUser;
import io.jsonwebtoken.*;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.time.Duration;
import java.time.Instant;
import java.util.*;

/**
 * JWT Token 生成/解析/校验组件
 *
 * <pre>{@code
 * // 生成 Token
 * String accessToken  = jwtTokenProvider.generateAccessToken(loginUser);
 * String refreshToken = jwtTokenProvider.generateRefreshToken(loginUser);
 *
 * // 解析用户信息
 * LoginUser user = jwtTokenProvider.parseToken(token);
 *
 * // 注销（加入黑名单）
 * jwtTokenProvider.invalidate(token);
 * }</pre>
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class JwtTokenProvider {

    private final JwtProperties jwtProperties;
    private final StringRedisTemplate redisTemplate;

    private SecretKey secretKey;

    @PostConstruct
    public void init() {
        byte[] keyBytes = Decoders.BASE64.decode(jwtProperties.getSecret());
        this.secretKey  = Keys.hmacShaKeyFor(keyBytes);
    }

    // ──────────────────── 生成 Token ────────────────────

    /**
     * 生成 Access Token
     */
    public String generateAccessToken(LoginUser user) {
        return buildToken(user, jwtProperties.getAccessTokenExpire(), "access");
    }

    /**
     * 生成 Refresh Token
     */
    public String generateRefreshToken(LoginUser user) {
        return buildToken(user, jwtProperties.getRefreshTokenExpire(), "refresh");
    }

    private String buildToken(LoginUser user, long expireSeconds, String tokenType) {
        Instant now     = Instant.now();
        Instant expiry  = now.plusSeconds(expireSeconds);

        return Jwts.builder()
                .id(UUID.randomUUID().toString())
                .issuer(jwtProperties.getIssuer())
                .subject(String.valueOf(user.getUserId()))
                .issuedAt(Date.from(now))
                .expiration(Date.from(expiry))
                .claim(CommonConstants.JWT_CLAIM_USER_ID,   user.getUserId())
                .claim(CommonConstants.JWT_CLAIM_USERNAME,  user.getUsername())
                .claim(CommonConstants.JWT_CLAIM_ROLES,     user.getRoles())
                .claim(CommonConstants.JWT_CLAIM_TENANT_ID, user.getTenantId())
                .claim("tokenType", tokenType)
                .signWith(secretKey, Jwts.SIG.HS256)
                .compact();
    }

    // ──────────────────── 解析 Token ────────────────────

    /**
     * 解析 Token，返回 Claims
     *
     * @throws JwtException Token 无效或过期
     */
    public Claims parseToken(String token) {
        return Jwts.parser()
                .verifyWith(secretKey)
                .requireIssuer(jwtProperties.getIssuer())
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    /**
     * 解析 Token，构建 LoginUser
     */
    @SuppressWarnings("unchecked")
    public LoginUser parseToLoginUser(String token) {
        Claims claims = parseToken(token);

        return LoginUser.builder()
                .userId(claims.get(CommonConstants.JWT_CLAIM_USER_ID, Long.class))
                .username(claims.get(CommonConstants.JWT_CLAIM_USERNAME, String.class))
                .roles((List<String>) claims.getOrDefault(CommonConstants.JWT_CLAIM_ROLES, List.of()))
                .tenantId(claims.get(CommonConstants.JWT_CLAIM_TENANT_ID, String.class))
                .build();
    }

    // ──────────────────── 校验 ────────────────────

    /**
     * 校验 Token（含黑名单检查）
     *
     * @return true=有效, false=无效/过期/已注销
     */
    public boolean validateToken(String token) {
        try {
            Claims claims = parseToken(token);
            // 检查黑名单
            String jti = claims.getId();
            Boolean inBlacklist = redisTemplate.hasKey(jwtProperties.getBlacklistKeyPrefix() + jti);
            return !Boolean.TRUE.equals(inBlacklist);
        } catch (ExpiredJwtException e) {
            log.debug("[JWT] Token 已过期: {}", e.getMessage());
            return false;
        } catch (JwtException e) {
            log.warn("[JWT] Token 无效: {}", e.getMessage());
            return false;
        }
    }

    /**
     * 校验是否 Refresh Token
     */
    public boolean isRefreshToken(String token) {
        try {
            Claims claims = parseToken(token);
            return "refresh".equals(claims.get("tokenType"));
        } catch (JwtException e) {
            return false;
        }
    }

    /**
     * 获取 Token 剩余有效秒数（已过期返回 0）
     */
    public long getRemainingSeconds(String token) {
        try {
            Claims claims  = parseToken(token);
            long expireMs  = claims.getExpiration().getTime();
            long remainMs  = expireMs - Instant.now().toEpochMilli();
            return Math.max(0L, remainMs / 1000);
        } catch (JwtException e) {
            return 0L;
        }
    }

    // ──────────────────── 注销（黑名单） ────────────────────

    /**
     * 将 Token 加入黑名单（注销）
     */
    public void invalidate(String token) {
        try {
            Claims claims = parseToken(token);
            String jti    = claims.getId();
            long remaining = getRemainingSeconds(token);
            if (remaining > 0) {
                redisTemplate.opsForValue().set(
                        jwtProperties.getBlacklistKeyPrefix() + jti,
                        "1",
                        Duration.ofSeconds(remaining)
                );
            }
        } catch (JwtException e) {
            log.warn("[JWT] invalidate - 无效 Token: {}", e.getMessage());
        }
    }

    // ──────────────────── 工具方法 ────────────────────

    /**
     * 从 Authorization 请求头提取 Token
     */
    public static String extractFromHeader(String authHeader) {
        if (authHeader != null && authHeader.startsWith(CommonConstants.TOKEN_PREFIX)) {
            return authHeader.substring(CommonConstants.TOKEN_PREFIX.length());
        }
        return null;
    }
}
