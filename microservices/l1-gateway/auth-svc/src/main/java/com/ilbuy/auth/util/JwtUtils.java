package com.ilbuy.auth.util;

import com.ilbuy.auth.config.JwtProperties;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.UUID;

/**
 * JWT 工具类：签发 / 解析 / 校验
 *
 * <p>Payload 说明：
 * <ul>
 *   <li>sub    - userId（String）</li>
 *   <li>jti    - 唯一 tokenId，用于黑名单</li>
 *   <li>userType - "BUSINESS" | "CONSUMER"</li>
 *   <li>roles  - 逗号分隔角色，如 "ROLE_ENTERPRISE,ROLE_USER"</li>
 *   <li>iat    - 签发时间</li>
 *   <li>exp    - 过期时间</li>
 * </ul>
 *
 * @author ILbuy Team
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class JwtUtils {

    private final JwtProperties jwtProperties;

    /**
     * 签发访问令牌
     */
    public String generateAccessToken(String userId, String userType, String roles) {
        return buildToken(userId, userType, roles, jwtProperties.getAccessTokenTtl());
    }

    /**
     * 签发刷新令牌（无 claims，只携带 jti）
     */
    public String generateRefreshToken(String userId) {
        SecretKey key = getSigningKey();
        return Jwts.builder()
            .subject(userId)
            .id(UUID.randomUUID().toString())
            .claim("type", "refresh")
            .issuedAt(new Date())
            .expiration(new Date(System.currentTimeMillis() + jwtProperties.getRefreshTokenTtl() * 1000L))
            .signWith(key)
            .compact();
    }

    /**
     * 解析令牌，抛出异常表示无效（由调用方处理）
     */
    public Claims parseToken(String token) {
        return Jwts.parser()
            .verifyWith(getSigningKey())
            .build()
            .parseSignedClaims(token)
            .getPayload();
    }

    /**
     * 安静解析（不抛异常，失败返回 null）
     */
    public Claims parseTokenQuietly(String token) {
        try {
            return parseToken(token);
        } catch (JwtException | IllegalArgumentException e) {
            log.debug("Token 解析失败: {}", e.getMessage());
            return null;
        }
    }

    /**
     * 提取 jti（Token唯一ID，用于黑名单）
     */
    public String extractJti(String token) {
        Claims claims = parseTokenQuietly(token);
        return claims != null ? claims.getId() : null;
    }

    /**
     * 提取 userId
     */
    public String extractUserId(String token) {
        Claims claims = parseTokenQuietly(token);
        return claims != null ? claims.getSubject() : null;
    }

    // ============ 私有方法 ============

    private String buildToken(String userId, String userType, String roles, long ttlSeconds) {
        SecretKey key = getSigningKey();
        return Jwts.builder()
            .subject(userId)
            .id(UUID.randomUUID().toString())
            .claim("userType", userType)
            .claim("roles", roles)
            .claim("type", "access")
            .issuedAt(new Date())
            .expiration(new Date(System.currentTimeMillis() + ttlSeconds * 1000L))
            .signWith(key)
            .compact();
    }

    private SecretKey getSigningKey() {
        return Keys.hmacShaKeyFor(jwtProperties.getSecret().getBytes(StandardCharsets.UTF_8));
    }
}
