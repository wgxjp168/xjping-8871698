package com.health.physical.common.util;

import cn.hutool.core.date.DateUtil;
import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import lombok.extern.slf4j.Slf4j;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.Map;

/**
 * JWT 工具类
 */
@Slf4j
public class JwtUtil {

    private static final String DEFAULT_SECRET = "physical_health_system_jwt_secret_key_2024_secure_enough";

    private static SecretKey getKey(String secret) {
        byte[] keyBytes = secret.getBytes(StandardCharsets.UTF_8);
        // Ensure key is at least 32 bytes for HS256
        if (keyBytes.length < 32) {
            byte[] padded = new byte[32];
            System.arraycopy(keyBytes, 0, padded, 0, keyBytes.length);
            keyBytes = padded;
        }
        return Keys.hmacShaKeyFor(keyBytes);
    }

    /**
     * 生成Token
     */
    public static String generateToken(String subject, Map<String, Object> claims, long expireSeconds) {
        return generateToken(subject, claims, expireSeconds, DEFAULT_SECRET);
    }

    public static String generateToken(String subject, Map<String, Object> claims, long expireSeconds, String secret) {
        Date now = new Date();
        Date expiry = DateUtil.offsetSecond(now, (int) expireSeconds);
        return Jwts.builder()
                .setSubject(subject)
                .addClaims(claims)
                .setIssuedAt(now)
                .setExpiration(expiry)
                .signWith(getKey(secret), SignatureAlgorithm.HS256)
                .compact();
    }

    /**
     * 解析Token，返回Claims；无效Token返回null
     */
    public static Claims parseToken(String token) {
        return parseToken(token, DEFAULT_SECRET);
    }

    public static Claims parseToken(String token, String secret) {
        try {
            return Jwts.parserBuilder()
                    .setSigningKey(getKey(secret))
                    .build()
                    .parseClaimsJws(token)
                    .getBody();
        } catch (ExpiredJwtException e) {
            log.warn("Token已过期: {}", e.getMessage());
        } catch (JwtException e) {
            log.warn("Token无效: {}", e.getMessage());
        }
        return null;
    }

    /**
     * 获取subject
     */
    public static String getSubject(String token) {
        Claims claims = parseToken(token);
        return claims != null ? claims.getSubject() : null;
    }

    /**
     * 验证Token是否有效
     */
    public static boolean isValid(String token) {
        return parseToken(token) != null;
    }
}
