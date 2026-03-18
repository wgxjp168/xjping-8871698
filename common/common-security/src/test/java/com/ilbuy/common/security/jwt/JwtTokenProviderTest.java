package com.ilbuy.common.security.jwt;

import com.ilbuy.common.security.model.LoginUser;
import io.jsonwebtoken.Claims;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.List;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

@DisplayName("JwtTokenProvider 单元测试")
@ExtendWith(MockitoExtension.class)
class JwtTokenProviderTest {

    // 256-bit Base64 密钥（测试用）
    private static final String TEST_SECRET =
            "dGVzdC1zZWNyZXQta2V5LXRoYXQtaXMtYXQtbGVhc3QtMjU2LWJpdHMtbG9uZw==";

    @Mock
    private StringRedisTemplate redisTemplate;

    @Mock
    private ValueOperations<String, String> valueOps;

    private JwtTokenProvider jwtTokenProvider;
    private LoginUser testUser;

    @BeforeEach
    void setUp() {
        JwtProperties props = new JwtProperties();
        props.setSecret(TEST_SECRET);
        props.setAccessTokenExpire(3600L);
        props.setRefreshTokenExpire(86400L);
        props.setIssuer("ilbuy-test");
        props.setBlacklistKeyPrefix("ilbuy:token:blacklist:");

        jwtTokenProvider = new JwtTokenProvider(props, redisTemplate);
        jwtTokenProvider.init();

        testUser = LoginUser.builder()
                .userId(1001L)
                .username("testuser")
                .roles(List.of("ROLE_USER", "ROLE_ADMIN"))
                .tenantId("tenant-001")
                .build();
    }

    @Test
    @DisplayName("生成 Access Token 非空")
    void generateAccessToken_notBlank() {
        String token = jwtTokenProvider.generateAccessToken(testUser);
        assertThat(token).isNotBlank();
    }

    @Test
    @DisplayName("生成 Refresh Token 非空且与 Access Token 不同")
    void generateRefreshToken_differentFromAccess() {
        String accessToken  = jwtTokenProvider.generateAccessToken(testUser);
        String refreshToken = jwtTokenProvider.generateRefreshToken(testUser);
        assertThat(refreshToken).isNotBlank().isNotEqualTo(accessToken);
    }

    @Test
    @DisplayName("解析 Token 可取回 userId 和 username")
    void parseToLoginUser_returnsCorrectUser() {
        String token    = jwtTokenProvider.generateAccessToken(testUser);
        LoginUser parsed = jwtTokenProvider.parseToLoginUser(token);
        assertThat(parsed.getUserId()).isEqualTo(testUser.getUserId());
        assertThat(parsed.getUsername()).isEqualTo(testUser.getUsername());
        assertThat(parsed.getRoles()).containsAll(testUser.getRoles());
    }

    @Test
    @DisplayName("有效 Token 通过校验（不在黑名单）")
    void validateToken_valid() {
        String token = jwtTokenProvider.generateAccessToken(testUser);
        when(redisTemplate.hasKey(anyString())).thenReturn(Boolean.FALSE);
        assertThat(jwtTokenProvider.validateToken(token)).isTrue();
    }

    @Test
    @DisplayName("黑名单 Token 校验失败")
    void validateToken_blacklisted() {
        String token = jwtTokenProvider.generateAccessToken(testUser);
        when(redisTemplate.hasKey(anyString())).thenReturn(Boolean.TRUE);
        assertThat(jwtTokenProvider.validateToken(token)).isFalse();
    }

    @Test
    @DisplayName("篡改 Token 校验失败")
    void validateToken_tampered() {
        String token    = jwtTokenProvider.generateAccessToken(testUser);
        String tampered = token + "xxx";
        // 无需 Redis mock，直接抛 JwtException
        assertThat(jwtTokenProvider.validateToken(tampered)).isFalse();
    }

    @Test
    @DisplayName("isRefreshToken 正确识别类型")
    void isRefreshToken_correctType() {
        String accessToken  = jwtTokenProvider.generateAccessToken(testUser);
        String refreshToken = jwtTokenProvider.generateRefreshToken(testUser);
        assertThat(jwtTokenProvider.isRefreshToken(accessToken)).isFalse();
        assertThat(jwtTokenProvider.isRefreshToken(refreshToken)).isTrue();
    }

    @Test
    @DisplayName("getRemainingSeconds 在过期前大于 0")
    void getRemainingSeconds_positive() {
        String token = jwtTokenProvider.generateAccessToken(testUser);
        long remaining = jwtTokenProvider.getRemainingSeconds(token);
        assertThat(remaining).isPositive().isLessThanOrEqualTo(3600L);
    }

    @Test
    @DisplayName("extractFromHeader 正确提取 Bearer Token")
    void extractFromHeader() {
        String extracted = JwtTokenProvider.extractFromHeader("Bearer mytoken123");
        assertThat(extracted).isEqualTo("mytoken123");
    }

    @Test
    @DisplayName("extractFromHeader - 非 Bearer 返回 null")
    void extractFromHeader_notBearer() {
        assertThat(JwtTokenProvider.extractFromHeader("Basic xxxxx")).isNull();
        assertThat(JwtTokenProvider.extractFromHeader(null)).isNull();
    }

    @Test
    @DisplayName("Claims 包含 issuer")
    void claims_issuer() {
        String token  = jwtTokenProvider.generateAccessToken(testUser);
        Claims claims = jwtTokenProvider.parseToken(token);
        assertThat(claims.getIssuer()).isEqualTo("ilbuy-test");
    }
}
