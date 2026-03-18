package com.ilbuy.common.security.jwt;

import com.ilbuy.common.core.constants.CommonConstants;
import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.common.core.enums.ResultCode;
import com.ilbuy.common.security.model.LoginUser;
import com.ilbuy.common.security.token.ClientType;
import io.jsonwebtoken.*;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import javax.crypto.SecretKey;
import java.time.Duration;
import java.time.Instant;
import java.util.*;

/**
 * JWT Token 生成/解析/校验组件（支持多端鉴权和自定义过期时间）
 *
 * <pre>{@code
 * // 1. 默认生成（使用全局配置）
 * String accessToken  = jwtTokenProvider.generateAccessToken(loginUser);
 *
 * // 2. 多端鉴权：按客户端类型生成（不同端不同有效期）
 * String mobileToken  = jwtTokenProvider.generateAccessToken(loginUser, ClientType.MOBILE);
 * String adminToken   = jwtTokenProvider.generateAccessToken(loginUser, ClientType.ADMIN);
 *
 * // 3. 自定义过期时间（秒）
 * String shortToken   = jwtTokenProvider.generateAccessToken(loginUser, 600L);
 *
 * // 4. 刷新 Token
 * TokenPair pair = jwtTokenProvider.refreshTokenPair(refreshToken);
 *
 * // 5. 注销（加入黑名单）
 * jwtTokenProvider.invalidate(token);
 *
 * // 6. 注销用户所有端 Token
 * jwtTokenProvider.revokeAllUserTokens(userId);
 * }</pre>
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class JwtTokenProvider {

    private static final String CLAIM_TOKEN_TYPE   = "tokenType";
    private static final String CLAIM_CLIENT_TYPE  = "clientType";
    private static final String USER_TOKEN_SET_KEY = "ilbuy:user:tokens:";

    private final JwtProperties jwtProperties;
    private final StringRedisTemplate redisTemplate;

    private SecretKey secretKey;

    @PostConstruct
    public void init() {
        byte[] keyBytes = Decoders.BASE64.decode(jwtProperties.getSecret());
        this.secretKey  = Keys.hmacShaKeyFor(keyBytes);
    }

    // ═══════════════════════ 生成 Token ═══════════════════════

    /**
     * 生成 Access Token（使用全局配置过期时间，默认 WEB 端）
     */
    public String generateAccessToken(LoginUser user) {
        return generateAccessToken(user, ClientType.WEB);
    }

    /**
     * 生成 Access Token（按客户端类型，使用该端对应的过期策略）
     *
     * @param user       登录用户
     * @param clientType 客户端类型（MOBILE/WEB/ADMIN/OPEN/DEVICE）
     */
    public String generateAccessToken(LoginUser user, ClientType clientType) {
        long expire = clientType != null
                ? clientType.getAccessTokenExpire()
                : jwtProperties.getAccessTokenExpire();
        return buildToken(user, expire, "access",
                clientType != null ? clientType.getCode() : ClientType.WEB.getCode());
    }

    /**
     * 生成 Access Token（自定义过期时间，适用于短时授权码场景）
     *
     * @param user          登录用户
     * @param expireSeconds 自定义有效期（秒），必须 &gt; 0
     */
    public String generateAccessToken(LoginUser user, long expireSeconds) {
        if (expireSeconds <= 0) {
            throw new BizException(ResultCode.BAD_REQUEST, "Token 有效期必须大于 0");
        }
        return buildToken(user, expireSeconds, "access", ClientType.WEB.getCode());
    }

    /**
     * 生成 Refresh Token（默认 WEB 端）
     */
    public String generateRefreshToken(LoginUser user) {
        return generateRefreshToken(user, ClientType.WEB);
    }

    /**
     * 生成 Refresh Token（按客户端类型）
     *
     * @param user       登录用户
     * @param clientType 客户端类型
     */
    public String generateRefreshToken(LoginUser user, ClientType clientType) {
        long expire = clientType != null
                ? clientType.getRefreshTokenExpire()
                : jwtProperties.getRefreshTokenExpire();
        String jti = UUID.randomUUID().toString();
        String token = buildToken(user, expire, "refresh",
                clientType != null ? clientType.getCode() : ClientType.WEB.getCode(), jti);

        // 将 Refresh Token JTI 存入 Redis（用户维度），支持批量注销
        String userTokenKey = USER_TOKEN_SET_KEY + user.getUserId()
                + ":" + (clientType != null ? clientType.getCode() : "web");
        redisTemplate.opsForSet().add(userTokenKey, jti);
        redisTemplate.expire(userTokenKey, Duration.ofSeconds(expire));

        return token;
    }

    /**
     * 生成 Token 对（Access + Refresh，同端类型）
     *
     * @return TokenPair { accessToken, refreshToken, accessExpire, refreshExpire }
     */
    public TokenPair generateTokenPair(LoginUser user, ClientType clientType) {
        ClientType ct = clientType != null ? clientType : ClientType.WEB;
        return TokenPair.builder()
                .accessToken(generateAccessToken(user, ct))
                .refreshToken(generateRefreshToken(user, ct))
                .accessExpire(ct.getAccessTokenExpire())
                .refreshExpire(ct.getRefreshTokenExpire())
                .clientType(ct.getCode())
                .build();
    }

    /**
     * 刷新 Token 对（使用 Refresh Token 换取新的 Access Token）
     *
     * <p>刷新策略：</p>
     * <ul>
     *   <li>Refresh Token 有效且未被注销 → 颁发新 Access Token</li>
     *   <li>Refresh Token 剩余时间少于 1/4 → 同时刷新 Refresh Token（滑动续期）</li>
     *   <li>Refresh Token 无效/过期 → 抛 BizException(REFRESH_TOKEN_EXPIRED)</li>
     * </ul>
     */
    @SuppressWarnings("unchecked")
    public TokenPair refreshTokenPair(String refreshToken) {
        // 1. 校验 Refresh Token
        if (!validateToken(refreshToken)) {
            throw new BizException(ResultCode.REFRESH_TOKEN_EXPIRED);
        }
        if (!isRefreshToken(refreshToken)) {
            throw new BizException(ResultCode.TOKEN_INVALID, "不是合法的 Refresh Token");
        }

        // 2. 解析用户信息和客户端类型
        Claims claims    = parseToken(refreshToken);
        ClientType ct    = ClientType.of(claims.get(CLAIM_CLIENT_TYPE, String.class));
        LoginUser user   = LoginUser.builder()
                .userId(claims.get(CommonConstants.JWT_CLAIM_USER_ID, Long.class))
                .username(claims.get(CommonConstants.JWT_CLAIM_USERNAME, String.class))
                .roles((List<String>) claims.getOrDefault(CommonConstants.JWT_CLAIM_ROLES, List.of()))
                .tenantId(claims.get(CommonConstants.JWT_CLAIM_TENANT_ID, String.class))
                .build();

        // 3. 旧 Refresh Token 加入黑名单（防止重放）
        invalidate(refreshToken);

        // 4. 判断是否需要滑动续期 Refresh Token
        long remaining = getRemainingSeconds(refreshToken);
        boolean needNewRefresh = remaining < ct.getRefreshTokenExpire() / 4;

        String newAccessToken  = generateAccessToken(user, ct);
        String newRefreshToken = needNewRefresh ? generateRefreshToken(user, ct) : refreshToken;

        return TokenPair.builder()
                .accessToken(newAccessToken)
                .refreshToken(newRefreshToken)
                .accessExpire(ct.getAccessTokenExpire())
                .refreshExpire(ct.getRefreshTokenExpire())
                .clientType(ct.getCode())
                .build();
    }

    // ═══════════════════════ 核心构建方法 ═══════════════════════

    private String buildToken(LoginUser user, long expireSeconds,
                              String tokenType, String clientType) {
        return buildToken(user, expireSeconds, tokenType, clientType, UUID.randomUUID().toString());
    }

    private String buildToken(LoginUser user, long expireSeconds,
                              String tokenType, String clientType, String jti) {
        Instant now    = Instant.now();
        Instant expiry = now.plusSeconds(expireSeconds);

        return Jwts.builder()
                .id(jti)
                .issuer(jwtProperties.getIssuer())
                .subject(String.valueOf(user.getUserId()))
                .issuedAt(Date.from(now))
                .expiration(Date.from(expiry))
                .claim(CommonConstants.JWT_CLAIM_USER_ID,   user.getUserId())
                .claim(CommonConstants.JWT_CLAIM_USERNAME,  user.getUsername())
                .claim(CommonConstants.JWT_CLAIM_ROLES,     user.getRoles())
                .claim(CommonConstants.JWT_CLAIM_TENANT_ID, user.getTenantId())
                .claim(CLAIM_TOKEN_TYPE,  tokenType)
                .claim(CLAIM_CLIENT_TYPE, clientType)
                .signWith(secretKey, Jwts.SIG.HS256)
                .compact();
    }

    // ═══════════════════════ 解析 Token ═══════════════════════

    /**
     * 解析 Token，返回 Claims（抛 JwtException 表示无效）
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
     * 解析 Token，构建 LoginUser（含 clientType）
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

    /**
     * 获取 Token 的客户端类型
     */
    public ClientType getClientType(String token) {
        try {
            Claims claims = parseToken(token);
            return ClientType.of(claims.get(CLAIM_CLIENT_TYPE, String.class));
        } catch (JwtException e) {
            return ClientType.WEB;
        }
    }

    // ═══════════════════════ 校验 ═══════════════════════

    /**
     * 校验 Token 有效性（含过期检查 + 黑名单检查）
     *
     * @return true=有效
     */
    public boolean validateToken(String token) {
        if (!StringUtils.hasText(token)) return false;
        try {
            Claims claims = parseToken(token);
            String jti    = claims.getId();
            Boolean inBlacklist = redisTemplate.hasKey(jwtProperties.getBlacklistKeyPrefix() + jti);
            return !Boolean.TRUE.equals(inBlacklist);
        } catch (ExpiredJwtException e) {
            log.debug("[JWT] Token 已过期");
            return false;
        } catch (JwtException e) {
            log.warn("[JWT] Token 无效: {}", e.getMessage());
            return false;
        }
    }

    /**
     * 判断是否为 Refresh Token
     */
    public boolean isRefreshToken(String token) {
        try {
            return "refresh".equals(parseToken(token).get(CLAIM_TOKEN_TYPE));
        } catch (JwtException e) {
            return false;
        }
    }

    /**
     * 获取 Token 剩余有效秒数（已过期或无效返回 0）
     */
    public long getRemainingSeconds(String token) {
        try {
            Claims claims = parseToken(token);
            long remainMs = claims.getExpiration().getTime() - Instant.now().toEpochMilli();
            return Math.max(0L, remainMs / 1000);
        } catch (JwtException e) {
            return 0L;
        }
    }

    // ═══════════════════════ 注销 ═══════════════════════

    /**
     * 将 Token 加入黑名单（单 Token 注销）
     */
    public void invalidate(String token) {
        if (!StringUtils.hasText(token)) return;
        try {
            Claims claims  = parseToken(token);
            String jti     = claims.getId();
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

    /**
     * 注销指定用户的所有端 Refresh Token（全端踢出）
     *
     * <p>场景：修改密码、账号异常时强制下线所有设备</p>
     *
     * @param userId 用户 ID
     */
    public void revokeAllUserTokens(Long userId) {
        for (ClientType ct : ClientType.values()) {
            String key  = USER_TOKEN_SET_KEY + userId + ":" + ct.getCode();
            Set<String> jtis = redisTemplate.opsForSet().members(key);
            if (jtis != null) {
                jtis.forEach(jti ->
                        redisTemplate.opsForValue().set(
                                jwtProperties.getBlacklistKeyPrefix() + jti,
                                "1",
                                Duration.ofDays(30) // 黑名单 TTL 30天（覆盖最长 Refresh Token）
                        ));
            }
            redisTemplate.delete(key);
        }
        log.info("[JWT] 用户 {} 所有端 Token 已注销", userId);
    }

    /**
     * 注销指定用户指定端的 Refresh Token（单端踢出）
     *
     * @param userId     用户 ID
     * @param clientType 客户端类型
     */
    public void revokeUserTokensByClient(Long userId, ClientType clientType) {
        String key = USER_TOKEN_SET_KEY + userId + ":" + clientType.getCode();
        Set<String> jtis = redisTemplate.opsForSet().members(key);
        if (jtis != null) {
            jtis.forEach(jti ->
                    redisTemplate.opsForValue().set(
                            jwtProperties.getBlacklistKeyPrefix() + jti,
                            "1",
                            Duration.ofSeconds(clientType.getRefreshTokenExpire())
                    ));
        }
        redisTemplate.delete(key);
        log.info("[JWT] 用户 {} {} 端 Token 已注销", userId, clientType.getCode());
    }

    // ═══════════════════════ 工具方法 ═══════════════════════

    /**
     * 从 Authorization 请求头提取 Token（自动去除 Bearer 前缀）
     */
    public static String extractFromHeader(String authHeader) {
        if (StringUtils.hasText(authHeader)
                && authHeader.startsWith(CommonConstants.TOKEN_PREFIX)) {
            return authHeader.substring(CommonConstants.TOKEN_PREFIX.length());
        }
        return null;
    }
}
