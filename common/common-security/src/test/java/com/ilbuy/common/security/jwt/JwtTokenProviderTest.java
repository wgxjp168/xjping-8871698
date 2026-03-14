package com.ilbuy.common.security.jwt;

import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.common.core.result.ResultCode;
import io.jsonwebtoken.Claims;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * JWT Token Provider 单元测试
 *
 * @author ILbuy Team
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("JWT Token Provider 测试")
class JwtTokenProviderTest {

    @Mock
    private StringRedisTemplate redisTemplate;

    @Mock
    private ValueOperations<String, String> valueOps;

    private JwtTokenProvider jwtTokenProvider;
    private JwtProperties jwtProperties;

    private static final String USER_ID = "100001";
    private static final String USER_TYPE_B2C = "B2C";
    private static final String USER_TYPE_B2B = "B2B";
    private static final String MEMBER_LEVEL = "PRO";

    @BeforeEach
    void setUp() {
        jwtProperties = new JwtProperties();
        jwtProperties.setSecret("ilbuy-test-secret-key-must-be-at-least-32-chars");
        jwtProperties.setExpiration(7_200_000L);
        jwtProperties.setRefreshExpiration(604_800_000L);
        jwtProperties.setEnableBlacklist(false); // 测试中禁用黑名单

        when(redisTemplate.opsForValue()).thenReturn(valueOps);
        doNothing().when(valueOps).set(anyString(), anyString(), anyLong(), any());

        jwtTokenProvider = new JwtTokenProvider(jwtProperties, redisTemplate);
    }

    @Test
    @DisplayName("生成 Access Token 不为空")
    void testGenerateAccessToken() {
        String token = jwtTokenProvider.generateAccessToken(USER_ID, USER_TYPE_B2C, MEMBER_LEVEL);
        assertThat(token).isNotBlank();
        assertThat(token.split("\\.")).hasSize(3); // JWT由3段组成
    }

    @Test
    @DisplayName("解析 Token 获取正确的用户ID")
    void testParseTokenUserId() {
        String token = jwtTokenProvider.generateAccessToken(USER_ID, USER_TYPE_B2C, MEMBER_LEVEL);
        Claims claims = jwtTokenProvider.parseToken(token);
        assertThat(claims.getSubject()).isEqualTo(USER_ID);
    }

    @Test
    @DisplayName("解析 Token 获取正确的用户类型")
    void testParseTokenUserType() {
        String token = jwtTokenProvider.generateAccessToken(USER_ID, USER_TYPE_B2B, MEMBER_LEVEL);
        assertThat(jwtTokenProvider.getUserType(token)).isEqualTo(USER_TYPE_B2B);
    }

    @Test
    @DisplayName("有效 Token 校验通过")
    void testValidateTokenSuccess() {
        String token = jwtTokenProvider.generateAccessToken(USER_ID, USER_TYPE_B2C, MEMBER_LEVEL);
        assertThat(jwtTokenProvider.validateToken(token)).isTrue();
    }

    @Test
    @DisplayName("过期 Token 校验失败并抛出正确异常")
    void testExpiredTokenThrowsException() {
        // 生成1毫秒有效期的Token（立即过期）
        JwtProperties shortExpiry = new JwtProperties();
        shortExpiry.setSecret("ilbuy-test-secret-key-must-be-at-least-32-chars");
        shortExpiry.setExpiration(1L);
        shortExpiry.setEnableBlacklist(false);
        JwtTokenProvider provider = new JwtTokenProvider(shortExpiry, redisTemplate);

        String token = provider.generateAccessToken(USER_ID, USER_TYPE_B2C, MEMBER_LEVEL);

        // 等待1ms过期
        try { Thread.sleep(10); } catch (InterruptedException ignored) {}

        assertThatThrownBy(() -> provider.parseToken(token))
                .isInstanceOf(BizException.class)
                .satisfies(e -> assertThat(((BizException) e).getCode())
                        .isEqualTo(ResultCode.TOKEN_EXPIRED.getCode()));
    }

    @Test
    @DisplayName("篡改 Token 校验失败")
    void testTamperedTokenThrowsException() {
        String token = jwtTokenProvider.generateAccessToken(USER_ID, USER_TYPE_B2C, MEMBER_LEVEL);
        String tamperedToken = token + "tampered";
        assertThatThrownBy(() -> jwtTokenProvider.parseToken(tamperedToken))
                .isInstanceOf(BizException.class)
                .satisfies(e -> assertThat(((BizException) e).getCode())
                        .isEqualTo(ResultCode.TOKEN_INVALID.getCode()));
    }

    @Test
    @DisplayName("resolveToken 正确解析Bearer头")
    void testResolveToken() {
        String token = jwtTokenProvider.generateAccessToken(USER_ID, USER_TYPE_B2C, MEMBER_LEVEL);
        String bearerToken = "Bearer " + token;
        assertThat(jwtTokenProvider.resolveToken(bearerToken)).isEqualTo(token);
    }

    @Test
    @DisplayName("resolveToken 无Bearer前缀返回null")
    void testResolveTokenWithoutBearer() {
        assertThat(jwtTokenProvider.resolveToken("invalid-token")).isNull();
        assertThat(jwtTokenProvider.resolveToken(null)).isNull();
    }

    @Test
    @DisplayName("生成 Token 对包含 access 和 refresh")
    void testGenerateTokenPair() {
        JwtTokenProvider.TokenPair pair =
                jwtTokenProvider.generateTokenPair(USER_ID, USER_TYPE_B2C, MEMBER_LEVEL);
        assertThat(pair.accessToken()).isNotBlank();
        assertThat(pair.refreshToken()).isNotBlank();
        assertThat(pair.accessTokenExpireMs()).isEqualTo(jwtProperties.getExpiration());
    }
}
