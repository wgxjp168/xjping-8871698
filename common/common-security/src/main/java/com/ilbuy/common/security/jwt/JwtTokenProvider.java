package com.ilbuy.common.security.jwt;

import com.ilbuy.common.core.constant.CommonConstants;
import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.common.core.result.ResultCode;
import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import lombok.Getter;
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
 * <p><b>支持功能：</b>
 * <ul>
 *   <li>生成 Access Token / Refresh Token</li>
 *   <li><b>多端鉴权</b>：通过 {@link ClientType} 区分 Web/App/小程序，
 *       不同端可独立登出，互不影响</li>
 *   <li><b>自定义过期时间</b>：调用方可覆盖默认过期时间（满足"记住我"等场景）</li>
 *   <li>Token 黑名单（登出后立即失效，TTL=Token剩余有效期）</li>
 *   <li>Token 即将过期检测（剩余 &lt; 30min 时响应头携带提示）</li>
 *   <li>Refresh Token 刷新 Access Token</li>
 * </ul>
 *
 * <p><b>Token Claims 结构：</b>
 * <pre>
 * {
 *   "sub":         "userId",
 *   "userType":    "B2C",         // B2B / B2C
 *   "memberLevel": "PRO",         // FREE / BASIC / PRO / ENTERPRISE
 *   "clientType":  "APP",         // WEB / APP / MINIPROGRAM（多端鉴权核心字段）
 *   "type":        "access",      // access / refresh
 *   "iat":         1710000000,
 *   "exp":         1710007200
 * }
 * </pre>
 *
 * <p><b>多端设计说明：</b>
 * 每个端（Web/App/小程序）拥有独立的 Refresh Token，
 * Redis Key 格式：{@code ilbuy:token:refresh:{userId}:{clientType}}
 * 因此用户在 App 登出不影响 Web 端的登录状态。
 *
 * @author ILbuy Team
 * @version 1.1.0
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class JwtTokenProvider {

    private final JwtProperties jwtProperties;
    private final StringRedisTemplate redisTemplate;

    // ==================== Claims Key 常量 ====================
    private static final String CLAIM_USER_TYPE    = "userType";
    private static final String CLAIM_MEMBER_LEVEL = "memberLevel";
    private static final String CLAIM_CLIENT_TYPE  = "clientType";
    private static final String CLAIM_TOKEN_TYPE   = "type";

    private static final String TOKEN_TYPE_ACCESS  = "access";
    private static final String TOKEN_TYPE_REFRESH = "refresh";

    // ==================== 客户端类型枚举 ====================

    /**
     * 客户端类型（多端鉴权）
     */
    @Getter
    public enum ClientType {
        /** PC Web 端 */
        WEB("WEB"),
        /** 移动 App 端（Android/iOS）*/
        APP("APP"),
        /** 微信小程序 */
        MINIPROGRAM("MINIPROGRAM");

        private final String code;

        ClientType(String code) {
            this.code = code;
        }

        public static ClientType fromCode(String code) {
            if (code == null) return WEB;
            for (ClientType t : values()) {
                if (t.code.equalsIgnoreCase(code)) return t;
            }
            return WEB;
        }
    }

    // ==================== Token 生成 ====================

    /**
     * 生成 Access Token（使用配置文件中的默认过期时间）
     *
     * @param userId      用户ID
     * @param userType    用户类型（B2B / B2C）
     * @param memberLevel 会员等级
     * @param clientType  客户端类型（多端鉴权）
     * @return Access Token 字符串
     */
    public String generateAccessToken(
            String userId, String userType, String memberLevel, ClientType clientType) {
        return generateAccessToken(userId, userType, memberLevel, clientType,
                jwtProperties.getExpiration());
    }

    /**
     * 生成 Access Token（<b>支持自定义过期时间</b>）
     *
     * <p>使用场景：
     * <ul>
     *   <li>"记住我"功能：传入更长的过期时间（如30天）</li>
     *   <li>临时访问Token：传入更短的过期时间（如5分钟）</li>
     * </ul>
     *
     * @param userId        用户ID
     * @param userType      用户类型（B2B / B2C）
     * @param memberLevel   会员等级
     * @param clientType    客户端类型
     * @param expirationMs  自定义过期时间（毫秒）
     * @return Access Token 字符串
     */
    public String generateAccessToken(
            String userId, String userType, String memberLevel,
            ClientType clientType, long expirationMs) {
        Map<String, Object> claims = new HashMap<>();
        claims.put(CLAIM_USER_TYPE,    userType);
        claims.put(CLAIM_MEMBER_LEVEL, memberLevel);
        claims.put(CLAIM_CLIENT_TYPE,  clientType.getCode());
        claims.put(CLAIM_TOKEN_TYPE,   TOKEN_TYPE_ACCESS);
        return buildToken(userId, claims, expirationMs);
    }

    /**
     * 生成 Refresh Token（使用默认过期时间，存入 Redis）
     *
     * <p>Refresh Token 同样携带 userType / memberLevel / clientType，
     * 避免刷新时需要额外查数据库。
     *
     * @param userId      用户ID
     * @param userType    用户类型
     * @param memberLevel 会员等级
     * @param clientType  客户端类型（不同端独立存储）
     */
    public String generateRefreshToken(
            String userId, String userType, String memberLevel, ClientType clientType) {
        return generateRefreshToken(userId, userType, memberLevel, clientType,
                jwtProperties.getRefreshExpiration());
    }

    /**
     * 生成 Refresh Token（<b>支持自定义过期时间</b>）
     *
     * @param userId          用户ID
     * @param userType        用户类型
     * @param memberLevel     会员等级
     * @param clientType      客户端类型
     * @param expirationMs    自定义过期时间（毫秒）
     * @return Refresh Token 字符串
     */
    public String generateRefreshToken(
            String userId, String userType, String memberLevel,
            ClientType clientType, long expirationMs) {
        Map<String, Object> claims = new HashMap<>();
        claims.put(CLAIM_USER_TYPE,    userType);
        claims.put(CLAIM_MEMBER_LEVEL, memberLevel);
        claims.put(CLAIM_CLIENT_TYPE,  clientType.getCode());
        claims.put(CLAIM_TOKEN_TYPE,   TOKEN_TYPE_REFRESH);
        String refreshToken = buildToken(userId, claims, expirationMs);

        // 多端独立存储 Refresh Token，Key = refresh:{userId}:{clientType}
        String redisKey = buildRefreshTokenKey(userId, clientType);
        redisTemplate.opsForValue().set(redisKey, refreshToken, expirationMs, TimeUnit.MILLISECONDS);
        log.debug("[JWT] Refresh Token 已存储 Redis: key={}", redisKey);

        return refreshToken;
    }

    /**
     * 生成 Token 对（Access + Refresh）
     *
     * @param userId      用户ID
     * @param userType    用户类型
     * @param memberLevel 会员等级
     * @param clientType  客户端类型
     * @return {@link TokenPair}
     */
    public TokenPair generateTokenPair(
            String userId, String userType, String memberLevel, ClientType clientType) {
        return generateTokenPair(userId, userType, memberLevel, clientType,
                jwtProperties.getExpiration(), jwtProperties.getRefreshExpiration());
    }

    /**
     * 生成 Token 对（<b>支持自定义双Token过期时间</b>）
     *
     * @param userId               用户ID
     * @param userType             用户类型
     * @param memberLevel          会员等级
     * @param clientType           客户端类型
     * @param accessExpirationMs   Access Token 过期时间（毫秒）
     * @param refreshExpirationMs  Refresh Token 过期时间（毫秒）
     */
    public TokenPair generateTokenPair(
            String userId, String userType, String memberLevel, ClientType clientType,
            long accessExpirationMs, long refreshExpirationMs) {
        String accessToken  = generateAccessToken(userId, userType, memberLevel, clientType, accessExpirationMs);
        String refreshToken = generateRefreshToken(userId, userType, memberLevel, clientType, refreshExpirationMs);
        return new TokenPair(accessToken, refreshToken, accessExpirationMs, refreshExpirationMs, clientType);
    }

    // ==================== Token 解析 ====================

    /**
     * 解析 Token，返回 Claims
     *
     * @param token JWT Token 字符串（不含 Bearer 前缀）
     * @return Claims
     * @throws BizException {@link ResultCode#TOKEN_EXPIRED} Token 已过期
     * @throws BizException {@link ResultCode#TOKEN_INVALID} Token 无效/被篡改
     */
    public Claims parseToken(String token) {
        try {
            return Jwts.parser()
                    .verifyWith(getSigningKey())
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();
        } catch (ExpiredJwtException e) {
            log.debug("[JWT] Token 已过期: {}", e.getMessage());
            throw new BizException(ResultCode.TOKEN_EXPIRED);
        } catch (JwtException | IllegalArgumentException e) {
            log.warn("[JWT] Token 无效: {}", e.getMessage());
            throw new BizException(ResultCode.TOKEN_INVALID);
        }
    }

    /**
     * 从 Token 获取用户ID
     */
    public String getUserId(String token) {
        return parseToken(token).getSubject();
    }

    /**
     * 从 Token 获取用户类型（B2B / B2C）
     */
    public String getUserType(String token) {
        return (String) parseToken(token).get(CLAIM_USER_TYPE);
    }

    /**
     * 从 Token 获取客户端类型
     */
    public ClientType getClientType(String token) {
        String code = (String) parseToken(token).get(CLAIM_CLIENT_TYPE);
        return ClientType.fromCode(code);
    }

    // ==================== Token 校验 ====================

    /**
     * 校验 Token 是否有效（含黑名单检查）
     *
     * @param token JWT Token 字符串
     * @return true=有效，false=无效/已过期/已加入黑名单
     */
    public boolean validateToken(String token) {
        try {
            parseToken(token);  // 内部区分 Expired / Invalid 异常
            return !isTokenBlacklisted(token);
        } catch (BizException e) {
            return false;
        }
    }

    /**
     * 检测 Token 是否即将过期（剩余有效期 &lt; 30 分钟）
     * 用于前端 Token 静默续期策略
     */
    public boolean isTokenAboutToExpire(String token) {
        try {
            long exp = parseToken(token).getExpiration().getTime();
            return (exp - System.currentTimeMillis()) < 30L * 60 * 1000;
        } catch (BizException e) {
            return true;
        }
    }

    // ==================== Token 黑名单 ====================

    /**
     * Token 加入黑名单（登出 / 主动吊销）
     *
     * <p>黑名单 Redis Key TTL = Token 剩余有效期，到期自动清除，无需手动维护。
     *
     * @param token JWT Token 字符串
     */
    public void blacklistToken(String token) {
        if (!jwtProperties.isEnableBlacklist()) {
            return;
        }
        try {
            long exp = parseToken(token).getExpiration().getTime();
            long ttl = exp - System.currentTimeMillis();
            if (ttl > 0) {
                String key = buildBlacklistKey(token);
                redisTemplate.opsForValue().set(key, "1", ttl, TimeUnit.MILLISECONDS);
                log.info("[JWT] Token 已加入黑名单，TTL={}ms", ttl);
            }
        } catch (BizException e) {
            log.debug("[JWT] Token 已失效，无需加入黑名单");
        }
    }

    /**
     * 登出指定端（仅吊销该端的 Refresh Token，Access Token 等自然过期）
     *
     * @param userId     用户ID
     * @param clientType 要登出的客户端
     */
    public void logoutClient(String userId, ClientType clientType) {
        String key = buildRefreshTokenKey(userId, clientType);
        redisTemplate.delete(key);
        log.info("[JWT] 用户 {} 在 {} 端已登出", userId, clientType.getCode());
    }

    /**
     * 全端登出（吊销所有端的 Refresh Token）
     *
     * @param userId 用户ID
     */
    public void logoutAllClients(String userId) {
        for (ClientType clientType : ClientType.values()) {
            logoutClient(userId, clientType);
        }
        log.info("[JWT] 用户 {} 已全端登出", userId);
    }

    // ==================== Refresh Token 刷新 ====================

    /**
     * 使用 Refresh Token 刷新 Access Token
     *
     * <p>刷新流程：
     * <ol>
     *   <li>解析 Refresh Token，校验 type=refresh</li>
     *   <li>从 Redis 查询该用户+端的 Refresh Token 是否一致（防重放）</li>
     *   <li>从 Refresh Token Claims 中取用户信息生成新 Access Token</li>
     * </ol>
     *
     * @param refreshToken Refresh Token 字符串
     * @return 新的 Access Token
     * @throws BizException {@link ResultCode#TOKEN_INVALID} 非 Refresh Token
     * @throws BizException {@link ResultCode#REFRESH_TOKEN_EXPIRED} Redis 中 Refresh Token 不一致
     */
    public String refreshAccessToken(String refreshToken) {
        Claims claims = parseToken(refreshToken);

        // 1. 校验 Token 类型
        if (!TOKEN_TYPE_REFRESH.equals(claims.get(CLAIM_TOKEN_TYPE))) {
            throw new BizException(ResultCode.TOKEN_INVALID, "非 Refresh Token，无法刷新");
        }

        String userId      = claims.getSubject();
        String userType    = (String) claims.get(CLAIM_USER_TYPE);
        String memberLevel = (String) claims.get(CLAIM_MEMBER_LEVEL);
        ClientType clientType = ClientType.fromCode((String) claims.get(CLAIM_CLIENT_TYPE));

        // 2. 校验 Redis 中存储的 Refresh Token（防重放攻击）
        String stored = redisTemplate.opsForValue().get(buildRefreshTokenKey(userId, clientType));
        if (!refreshToken.equals(stored)) {
            throw new BizException(ResultCode.REFRESH_TOKEN_EXPIRED);
        }

        // 3. 生成新 Access Token（使用默认过期时间）
        return generateAccessToken(userId,
                userType    != null ? userType    : "B2C",
                memberLevel != null ? memberLevel : "FREE",
                clientType);
    }

    // ==================== Token 头部解析 ====================

    /**
     * 从 Authorization Header 解析 Token（去掉 "Bearer " 前缀）
     *
     * @param bearerToken Authorization Header 值
     * @return Token 字符串，格式不合法则返回 null
     */
    public String resolveToken(String bearerToken) {
        if (bearerToken != null && bearerToken.startsWith(jwtProperties.getTokenPrefix())) {
            return bearerToken.substring(jwtProperties.getTokenPrefix().length()).trim();
        }
        return null;
    }

    // ==================== 私有方法 ====================

    private String buildToken(String subject, Map<String, Object> claims, long expirationMs) {
        Date now = new Date();
        return Jwts.builder()
                .claims(claims)
                .subject(subject)
                .issuedAt(now)
                .expiration(new Date(now.getTime() + expirationMs))
                .signWith(getSigningKey(), Jwts.SIG.HS256)
                .compact();
    }

    private SecretKey getSigningKey() {
        return Keys.hmacShaKeyFor(
                jwtProperties.getSecret().getBytes(StandardCharsets.UTF_8));
    }

    private boolean isTokenBlacklisted(String token) {
        if (!jwtProperties.isEnableBlacklist()) {
            return false;
        }
        return Boolean.TRUE.equals(redisTemplate.hasKey(buildBlacklistKey(token)));
    }

    /** Redis Key：Refresh Token（多端隔离）*/
    private String buildRefreshTokenKey(String userId, ClientType clientType) {
        return CommonConstants.CACHE_TOKEN_PREFIX + "refresh:" + userId + ":" + clientType.getCode();
    }

    /** Redis Key：黑名单 */
    private String buildBlacklistKey(String token) {
        // 截取 token 后32位作为 key 后缀，避免 Key 过长
        String suffix = token.length() > 32 ? token.substring(token.length() - 32) : token;
        return CommonConstants.CACHE_TOKEN_PREFIX + "blacklist:" + suffix;
    }

    // ==================== 返回值 ====================

    /**
     * Token 对（Access Token + Refresh Token）
     *
     * @param accessToken          Access Token
     * @param refreshToken         Refresh Token
     * @param accessTokenExpireMs  Access Token 过期时间（毫秒）
     * @param refreshTokenExpireMs Refresh Token 过期时间（毫秒）
     * @param clientType           客户端类型
     */
    public record TokenPair(
            String accessToken,
            String refreshToken,
            long accessTokenExpireMs,
            long refreshTokenExpireMs,
            ClientType clientType
    ) {}
}
