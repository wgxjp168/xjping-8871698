package com.ilbuy.common.security.jwt;

import com.ilbuy.common.core.enums.ResultCode;
import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.common.security.model.LoginUser;
import com.ilbuy.common.security.token.ClientType;
import com.ilbuy.common.security.token.TokenPair;
import io.jsonwebtoken.Claims;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.SetOperations;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@DisplayName("JwtTokenProvider 全功能测试")
@ExtendWith(MockitoExtension.class)
class JwtTokenProviderTest {

    // 256-bit Base64 测试密钥（不可用于生产）
    private static final String TEST_SECRET =
            "dGVzdC1zZWNyZXQta2V5LXRoYXQtaXMtYXQtbGVhc3QtMjU2LWJpdHMtbG9uZw==";

    @Mock StringRedisTemplate redisTemplate;
    @Mock ValueOperations<String, String> valueOps;
    @Mock SetOperations<String, String> setOps;

    private JwtTokenProvider provider;
    private LoginUser testUser;

    @BeforeEach
    void setUp() {
        JwtProperties props = new JwtProperties();
        props.setSecret(TEST_SECRET);
        props.setAccessTokenExpire(3_600L);
        props.setRefreshTokenExpire(86_400L);
        props.setIssuer("ilbuy-test");
        props.setBlacklistKeyPrefix("ilbuy:token:blacklist:");

        provider = new JwtTokenProvider(props, redisTemplate);
        provider.init();

        testUser = LoginUser.builder()
                .userId(1001L)
                .username("zhang3")
                .roles(List.of("ROLE_USER", "ROLE_ADMIN"))
                .tenantId("t-001")
                .build();
    }

    // ───────── 基本生成 ─────────

    @Nested
    @DisplayName("Token 生成")
    class GenerateTests {

        @Test
        @DisplayName("默认 generateAccessToken 非空")
        void defaultAccess_notBlank() {
            String token = provider.generateAccessToken(testUser);
            assertThat(token).isNotBlank();
        }

        @ParameterizedTest(name = "ClientType={0}")
        @EnumSource(ClientType.class)
        @DisplayName("各端 generateAccessToken 均非空")
        void allClientTypes_notBlank(ClientType ct) {
            lenient().when(redisTemplate.opsForSet()).thenReturn(setOps);
            lenient().when(setOps.add(any(), any())).thenReturn(1L);
            lenient().when(redisTemplate.expire(any(), any())).thenReturn(true);

            String token = provider.generateAccessToken(testUser, ct);
            assertThat(token).isNotBlank();
        }

        @Test
        @DisplayName("不同端生成的 Token 内容不同（有效期不同）")
        void mobileAndAdmin_differentExpiry() throws InterruptedException {
            String mobileToken = provider.generateAccessToken(testUser, ClientType.MOBILE);
            String adminToken  = provider.generateAccessToken(testUser, ClientType.ADMIN);
            // 过期时间写入 Claims，两者不同
            Claims mobileClaims = provider.parseToken(mobileToken);
            Claims adminClaims  = provider.parseToken(adminToken);
            assertThat(mobileClaims.getExpiration()).isAfter(adminClaims.getExpiration());
        }

        @Test
        @DisplayName("自定义过期时间生成 Token")
        void customExpire_tokenValid() {
            String token    = provider.generateAccessToken(testUser, 600L);
            long remaining  = provider.getRemainingSeconds(token);
            assertThat(remaining).isPositive().isLessThanOrEqualTo(600L);
        }

        @Test
        @DisplayName("自定义过期时间 <= 0 抛 BizException")
        void customExpire_invalid() {
            assertThatThrownBy(() -> provider.generateAccessToken(testUser, 0L))
                    .isInstanceOf(BizException.class);
            assertThatThrownBy(() -> provider.generateAccessToken(testUser, -1L))
                    .isInstanceOf(BizException.class);
        }

        @Test
        @DisplayName("generateTokenPair 返回 accessToken + refreshToken")
        void generateTokenPair_containsBothTokens() {
            when(redisTemplate.opsForSet()).thenReturn(setOps);
            when(setOps.add(any(), any())).thenReturn(1L);
            when(redisTemplate.expire(any(), any())).thenReturn(true);

            TokenPair pair = provider.generateTokenPair(testUser, ClientType.WEB);
            assertThat(pair.getAccessToken()).isNotBlank();
            assertThat(pair.getRefreshToken()).isNotBlank();
            assertThat(pair.getClientType()).isEqualTo("web");
            assertThat(pair.getAccessExpire()).isEqualTo(ClientType.WEB.getAccessTokenExpire());
        }
    }

    // ───────── 解析 ─────────

    @Nested
    @DisplayName("Token 解析")
    class ParseTests {

        @Test
        @DisplayName("解析 userId 和 username 正确")
        void parseToLoginUser_correctFields() {
            String token     = provider.generateAccessToken(testUser);
            LoginUser parsed = provider.parseToLoginUser(token);
            assertThat(parsed.getUserId()).isEqualTo(1001L);
            assertThat(parsed.getUsername()).isEqualTo("zhang3");
            assertThat(parsed.getRoles()).containsExactlyInAnyOrder("ROLE_USER", "ROLE_ADMIN");
            assertThat(parsed.getTenantId()).isEqualTo("t-001");
        }

        @Test
        @DisplayName("Claims 中含正确 issuer")
        void claims_correctIssuer() {
            Claims claims = provider.parseToken(provider.generateAccessToken(testUser));
            assertThat(claims.getIssuer()).isEqualTo("ilbuy-test");
        }

        @Test
        @DisplayName("getClientType 返回正确的端类型")
        void getClientType_correct() {
            String token = provider.generateAccessToken(testUser, ClientType.ADMIN);
            assertThat(provider.getClientType(token)).isEqualTo(ClientType.ADMIN);
        }

        @Test
        @DisplayName("isRefreshToken 正确区分 access / refresh")
        void isRefreshToken_discriminates() {
            when(redisTemplate.opsForSet()).thenReturn(setOps);
            when(setOps.add(any(), any())).thenReturn(1L);
            when(redisTemplate.expire(any(), any())).thenReturn(true);

            String access  = provider.generateAccessToken(testUser);
            String refresh = provider.generateRefreshToken(testUser);
            assertThat(provider.isRefreshToken(access)).isFalse();
            assertThat(provider.isRefreshToken(refresh)).isTrue();
        }
    }

    // ───────── 校验 ─────────

    @Nested
    @DisplayName("Token 校验")
    class ValidateTests {

        @Test
        @DisplayName("有效 Token 不在黑名单 → 校验通过")
        void valid_notBlacklisted_passes() {
            String token = provider.generateAccessToken(testUser);
            when(redisTemplate.hasKey(anyString())).thenReturn(Boolean.FALSE);
            assertThat(provider.validateToken(token)).isTrue();
        }

        @Test
        @DisplayName("在黑名单中的 Token → 校验失败")
        void blacklisted_fails() {
            String token = provider.generateAccessToken(testUser);
            when(redisTemplate.hasKey(anyString())).thenReturn(Boolean.TRUE);
            assertThat(provider.validateToken(token)).isFalse();
        }

        @Test
        @DisplayName("篡改签名 → 校验失败")
        void tampered_fails() {
            String token    = provider.generateAccessToken(testUser);
            String tampered = token.substring(0, token.lastIndexOf('.') + 1) + "XXXX";
            assertThat(provider.validateToken(tampered)).isFalse();
        }

        @Test
        @DisplayName("null/空 Token → 校验失败")
        void nullOrBlank_fails() {
            assertThat(provider.validateToken(null)).isFalse();
            assertThat(provider.validateToken("")).isFalse();
            assertThat(provider.validateToken("   ")).isFalse();
        }

        @Test
        @DisplayName("getRemainingSeconds 在有效期内为正数")
        void remainingSeconds_positive() {
            String token = provider.generateAccessToken(testUser);
            long remaining = provider.getRemainingSeconds(token);
            assertThat(remaining).isPositive().isLessThanOrEqualTo(3600L);
        }
    }

    // ───────── 注销 ─────────

    @Nested
    @DisplayName("Token 注销")
    class InvalidateTests {

        @Test
        @DisplayName("invalidate 将 jti 写入 Redis 黑名单")
        void invalidate_writesToBlacklist() {
            when(redisTemplate.opsForValue()).thenReturn(valueOps);
            String token = provider.generateAccessToken(testUser);
            provider.invalidate(token);
            verify(valueOps, times(1)).set(anyString(), eq("1"), any());
        }

        @Test
        @DisplayName("revokeAllUserTokens 遍历所有端")
        void revokeAllUserTokens_allClientsCovered() {
            when(redisTemplate.opsForSet()).thenReturn(setOps);
            when(setOps.members(anyString())).thenReturn(Set.of("jti-001", "jti-002"));
            when(redisTemplate.opsForValue()).thenReturn(valueOps);
            doNothing().when(valueOps).set(anyString(), anyString(), any());
            when(redisTemplate.delete(anyString())).thenReturn(true);

            provider.revokeAllUserTokens(1001L);

            // 每个 ClientType 都应查询 Redis Set
            verify(setOps, times(ClientType.values().length)).members(anyString());
        }
    }

    // ───────── 工具方法 ─────────

    @Nested
    @DisplayName("工具方法")
    class UtilsTests {

        @Test
        @DisplayName("extractFromHeader - Bearer 前缀正确提取")
        void extractFromHeader_bearer() {
            assertThat(JwtTokenProvider.extractFromHeader("Bearer mytoken")).isEqualTo("mytoken");
        }

        @Test
        @DisplayName("extractFromHeader - 非 Bearer 返回 null")
        void extractFromHeader_nonBearer() {
            assertThat(JwtTokenProvider.extractFromHeader("Basic xxx")).isNull();
            assertThat(JwtTokenProvider.extractFromHeader(null)).isNull();
            assertThat(JwtTokenProvider.extractFromHeader("")).isNull();
        }
    }

    // ───────── Refresh Token 刷新 ─────────

    @Nested
    @DisplayName("refreshTokenPair 刷新逻辑")
    class RefreshTests {

        @Test
        @DisplayName("有效 Refresh Token 刷新成功，返回新 Access Token")
        void refresh_success() {
            when(redisTemplate.opsForSet()).thenReturn(setOps);
            when(setOps.add(any(), any())).thenReturn(1L);
            when(redisTemplate.expire(any(), any())).thenReturn(true);

            String refreshToken = provider.generateRefreshToken(testUser, ClientType.WEB);

            // refresh 时的 mock：validateToken（不在黑名单）+ invalidate + 生成新 token
            when(redisTemplate.hasKey(anyString())).thenReturn(Boolean.FALSE);
            when(redisTemplate.opsForValue()).thenReturn(valueOps);
            doNothing().when(valueOps).set(anyString(), anyString(), any());

            TokenPair newPair = provider.refreshTokenPair(refreshToken);
            assertThat(newPair.getAccessToken()).isNotBlank();
            assertThat(newPair.getClientType()).isEqualTo("web");
        }

        @Test
        @DisplayName("用 Access Token 调用 refresh → 抛 BizException(TOKEN_INVALID)")
        void refresh_withAccessToken_throws() {
            String accessToken = provider.generateAccessToken(testUser);
            when(redisTemplate.hasKey(anyString())).thenReturn(Boolean.FALSE);

            assertThatThrownBy(() -> provider.refreshTokenPair(accessToken))
                    .isInstanceOf(BizException.class)
                    .satisfies(e -> assertThat(((BizException) e).getCode())
                            .isEqualTo(ResultCode.TOKEN_INVALID.getCode()));
        }
    }
}
