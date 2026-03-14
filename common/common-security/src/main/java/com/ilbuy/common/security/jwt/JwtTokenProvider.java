package com.ilbuy.common.security.jwt;

import com.ilbuy.common.core.constant.CommonConstants;
import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.common.core.result.ResultCode;
import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * JWT Token 核心工具类
 *
 * <p>功能：
 * <ul>
 *   <li>生成 Access Token / Refresh Token</li>
 *   <li>解析和校验 Token</li>
 *   <li>Token 黑名单管理（登出时加入黑名单）</li>
 *   <li>Token 自动续期检查</li>
 * </ul>
 *
 * <p>Token Claims结构：
 * <pre>
 * {
 *   "sub": "userId",
 *   "userType": "B2C",         // B2B/B2C
 *   "memberLevel": "PRO",      // 会员等级
 *   "type": "access",          // access/refresh
 *   "iat": 1710000000,
 *   "exp": 1710007200
 * }
 * </pre>
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class JwtTokenProvider {

    private final JwtProperties jwtProperties;
    private final StringRedisTemplate redisTemplate;

    /** Token类型 - Access */
    private static final String TOKEN_TYPE_ACCESS = "access";
    /** Token类型 - Refresh */
    private static final String TOKEN_TYPE_REFRESH = "refresh";
    /** Claims Key - 用户类型 */
    private static final String CLAIM_USER_TYPE = "userType";
    /** Claims Key - 会员等级 */
    private static final String CLAIM_MEMBER_LEVEL = "memberLevel";
    /** Claims Key - Token类型 */
    private static final String CLAIM_TOKEN_TYPE = "type";

    /**
     * 生成 Access Token
     *
     * @param userId      用户ID
     * @param userType    用户类型（B2B/B2C）
     * @param memberLevel 会员等级
     * @return Access Token 字符串
     */
    public String generateAccessToken(String userId, String userType, String memberLevel) {
        Map<String, Object> claims = new HashMap<>();
        claims.put(CLAIM_USER_TYPE, userType);
        claims.put(CLAIM_MEMBER_LEVEL, memberLevel);
        claims.put(CLAIM_TOKEN_TYPE, TOKEN_TYPE_ACCESS);
        return buildToken(userId, claims, jwtProperties.getExpiration());
    }

    /**
     * 生成 Refresh Token
     *
     * @param userId 用户ID
     * @return Refresh Token 字符串
     */
    public String generateRefreshToken(String userId) {
        Map<String, Object> claims = new HashMap<>();
        claims.put(CLAIM_TOKEN_TYPE, TOKEN_TYPE_REFRESH);
        String refreshToken = buildToken(userId, claims, jwtProperties.getRefreshExpiration());

        // 将RefreshToken存入Redis，支持主动吊销
        String redisKey = CommonConstants.CACHE_TOKEN_PREFIX + "refresh:" + userId;
        redisTemplate.opsForValue().set(
                redisKey, refreshToken,
                jwtProperties.getRefreshExpiration(), TimeUnit.MILLISECONDS);

        return refreshToken;
    }

    /**
     * 生成 Token 对（Access Token + Refresh Token）
     *
     * @param userId      用户ID
     * @param userType    用户类型
     * @param memberLevel 会员等级
     * @return TokenPair
     */
    public TokenPair generateTokenPair(String userId, String userType, String memberLevel) {
        String accessToken = generateAccessToken(userId, userType, memberLevel);
        String refreshToken = generateRefreshToken(userId);
        return new TokenPair(accessToken, refreshToken,
                jwtProperties.getExpiration(), jwtProperties.getRefreshExpiration());
    }

    /**
     * 解析 Token，返回 Claims
     *
     * @param token JWT Token字符串（不含Bearer前缀）
     * @return Claims
     * @throws BizException Token无效或已过期
     */
    public Claims parseToken(String token) {
        try {
            return Jwts.parser()
                    .verifyWith(getSigningKey())
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();
        } catch (ExpiredJwtException e) {
            log.debug("[JWT] Token已过期: {}", e.getMessage());
            throw new BizException(ResultCode.TOKEN_EXPIRED);
        } catch (JwtException | IllegalArgumentException e) {
            log.warn("[JWT] Token无效: {}", e.getMessage());
            throw new BizException(ResultCode.TOKEN_INVALID);
        }
    }

    /**
     * 从 Token 获取用户ID
     *
     * @param token JWT Token字符串
     */
    public String getUserId(String token) {
        return parseToken(token).getSubject();
    }

    /**
     * 从 Token 获取用户类型
     *
     * @param token JWT Token字符串
     */
    public String getUserType(String token) {
        return (String) parseToken(token).get(CLAIM_USER_TYPE);
    }

    /**
     * 校验 Token 是否有效（含黑名单检查）
     *
     * @param token JWT Token字符串
     * @return true-有效，false-无效
     */
    public boolean validateToken(String token) {
        try {
            Claims claims = parseToken(token);
            // 检查黑名单
            if (jwtProperties.isEnableBlacklist() && isTokenBlacklisted(token)) {
                log.debug("[JWT] Token在黑名单中");
                return false;
            }
            return true;
        } catch (BizException e) {
            return false;
        }
    }

    /**
     * Token 加入黑名单（用于登出或主动吊销）
     *
     * @param token JWT Token字符串
     */
    public void blacklistToken(String token) {
        if (!jwtProperties.isEnableBlacklist()) {
            return;
        }
        try {
            Claims claims = parseToken(token);
            long expiration = claims.getExpiration().getTime();
            long ttl = expiration - System.currentTimeMillis();
            if (ttl > 0) {
                String blacklistKey = CommonConstants.CACHE_TOKEN_PREFIX + "blacklist:" + token;
                redisTemplate.opsForValue().set(blacklistKey, "1", ttl, TimeUnit.MILLISECONDS);
                log.info("[JWT] Token已加入黑名单，TTL={}ms", ttl);
            }
        } catch (BizException e) {
            log.debug("[JWT] Token已失效，无需加入黑名单");
        }
    }

    /**
     * 使用 Refresh Token 刷新 Access Token
     *
     * @param refreshToken Refresh Token 字符串
     * @return 新的 Access Token
     */
    public String refreshAccessToken(String refreshToken) {
        Claims claims = parseToken(refreshToken);

        // 校验是否为RefreshToken
        String tokenType = (String) claims.get(CLAIM_TOKEN_TYPE);
        if (!TOKEN_TYPE_REFRESH.equals(tokenType)) {
            throw new BizException(ResultCode.TOKEN_INVALID, "非RefreshToken，无法刷新");
        }

        String userId = claims.getSubject();

        // 检查Redis中的RefreshToken是否一致（防止重放）
        String redisKey = CommonConstants.CACHE_TOKEN_PREFIX + "refresh:" + userId;
        String storedToken = redisTemplate.opsForValue().get(redisKey);
        if (!refreshToken.equals(storedToken)) {
            throw new BizException(ResultCode.REFRESH_TOKEN_EXPIRED);
        }

        // 获取用户信息并生成新 Access Token（实际应查DB获取最新用户信息）
        // 此处从RefreshToken Claims中取，实际项目中调用用户服务获取
        String userType = (String) claims.get(CLAIM_USER_TYPE);
        String memberLevel = (String) claims.get(CLAIM_MEMBER_LEVEL);
        if (userType == null) {
            userType = "B2C";
        }
        if (memberLevel == null) {
            memberLevel = "FREE";
        }

        return generateAccessToken(userId, userType, memberLevel);
    }

    /**
     * 解析 Token Header 中的 Token（去掉 Bearer 前缀）
     *
     * @param bearerToken Authorization Header值
     * @return Token字符串，无效则返回null
     */
    public String resolveToken(String bearerToken) {
        if (bearerToken != null && bearerToken.startsWith(jwtProperties.getTokenPrefix())) {
            return bearerToken.substring(jwtProperties.getTokenPrefix().length()).trim();
        }
        return null;
    }

    /**
     * 检查 Token 是否即将过期（剩余时间 < 30分钟），用于自动续期
     *
     * @param token JWT Token字符串
     * @return true-即将过期
     */
    public boolean isTokenAboutToExpire(String token) {
        try {
            Claims claims = parseToken(token);
            long expiration = claims.getExpiration().getTime();
            return (expiration - System.currentTimeMillis()) < 30 * 60 * 1000L;
        } catch (BizException e) {
            return true;
        }
    }

    // ==================== 私有方法 ====================

    private String buildToken(String subject, Map<String, Object> claims, long expirationMs) {
        Date now = new Date();
        Date expiration = new Date(now.getTime() + expirationMs);
        return Jwts.builder()
                .claims(claims)
                .subject(subject)
                .issuedAt(now)
                .expiration(expiration)
                .signWith(getSigningKey(), Jwts.SIG.HS256)
                .compact();
    }

    private SecretKey getSigningKey() {
        byte[] keyBytes = jwtProperties.getSecret().getBytes(StandardCharsets.UTF_8);
        return Keys.hmacShaKeyFor(keyBytes);
    }

    private boolean isTokenBlacklisted(String token) {
        String blacklistKey = CommonConstants.CACHE_TOKEN_PREFIX + "blacklist:" + token;
        return Boolean.TRUE.equals(redisTemplate.hasKey(blacklistKey));
    }

    // ==================== 内部类 ====================

    /**
     * Token对（Access + Refresh）
     */
    public record TokenPair(
            String accessToken,
            String refreshToken,
            long accessTokenExpireMs,
            long refreshTokenExpireMs
    ) {}
}
