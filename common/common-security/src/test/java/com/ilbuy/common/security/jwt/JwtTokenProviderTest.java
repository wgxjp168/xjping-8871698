package com.ilbuy.common.security.jwt;

import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.common.core.result.ResultCode;
import io.jsonwebtoken.Claims;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
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
 * JwtTokenProvider 单元测试
 *
 * <p>覆盖范围：
 * <ul>
 *   <li>基本 Token 生成/解析</li>
 *   <li>多端鉴权（WEB / APP / MINIPROGRAM 独立）</li>
 *   <li>自定义过期时间</li>
 *   <li>过期/篡改异常</li>
 *   <li>Token 对生成</li>
 *   <li>Refresh Token 解析</li>
 * </ul>
 *
 * @author ILbuy Team
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("JwtTokenProvider 测试")
class JwtTokenProviderTest {

    @Mock
    private StringRedisTemplate redisTemplate;

    @Mock
    private ValueOperations<String, String> valueOps;

    private JwtTokenProvider provider;
    private JwtProperties    props;

    private static final String USER_ID    = "100001";
    private static final String B2C        = "B2C";
    private static final String B2B        = "B2B";
    private static final String MEMBER_PRO = "PRO";

    @BeforeEach
    void setUp() {
        props = new JwtProperties();
        props.setSecret("ilbuy-test-secret-key-must-be-at-least-32-chars");
        props.setExpiration(7_200_000L);           // 2h
        props.setRefreshExpiration(604_800_000L);  // 7d
        props.setEnableBlacklist(false);           // 测试关闭黑名单

        // Mock Redis ValueOps（Refresh Token 写入）
        when(redisTemplate.opsForValue()).thenReturn(valueOps);
        doNothing().when(valueOps).set(anyString(), anyString(), anyLong(), any());

        provider = new JwtTokenProvider(props, redisTemplate);
    }

    // ================================================================
    //  基本功能
    // ================================================================

    @Nested
    @DisplayName("基本 Token 生成与解析")
    class BasicTokenTests {

        @Test
        @DisplayName("生成的 Token 为三段式 JWT 格式")
        void generateToken_jwtFormat() {
            String token = provider.generateAccessToken(
                    USER_ID, B2C, MEMBER_PRO, JwtTokenProvider.ClientType.WEB);
            assertThat(token).isNotBlank();
            assertThat(token.split("\\.")).hasSize(3);
        }

        @Test
        @DisplayName("解析 Token 用户ID正确")
        void parseToken_correctUserId() {
            String token = provider.generateAccessToken(
                    USER_ID, B2C, MEMBER_PRO, JwtTokenProvider.ClientType.APP);
            assertThat(provider.getUserId(token)).isEqualTo(USER_ID);
        }

        @Test
        @DisplayName("解析 Token 用户类型正确")
        void parseToken_correctUserType() {
            String token = provider.generateAccessToken(
                    USER_ID, B2B, MEMBER_PRO, JwtTokenProvider.ClientType.WEB);
            assertThat(provider.getUserType(token)).isEqualTo(B2B);
        }

        @Test
        @DisplayName("有效 Token 校验通过")
        void validateToken_validToken() {
            String token = provider.generateAccessToken(
                    USER_ID, B2C, MEMBER_PRO, JwtTokenProvider.ClientType.WEB);
            assertThat(provider.validateToken(token)).isTrue();
        }
    }

    // ================================================================
    //  多端鉴权
    // ================================================================

    @Nested
    @DisplayName("多端鉴权（WEB / APP / MINIPROGRAM）")
    class MultiClientTests {

        @Test
        @DisplayName("WEB 端 Token 包含 clientType=WEB")
        void webToken_containsClientType() {
            String token = provider.generateAccessToken(
                    USER_ID, B2C, MEMBER_PRO, JwtTokenProvider.ClientType.WEB);
            JwtTokenProvider.ClientType ct = provider.getClientType(token);
            assertThat(ct).isEqualTo(JwtTokenProvider.ClientType.WEB);
        }

        @Test
        @DisplayName("APP 端 Token 包含 clientType=APP")
        void appToken_containsClientType() {
            String token = provider.generateAccessToken(
                    USER_ID, B2C, MEMBER_PRO, JwtTokenProvider.ClientType.APP);
            assertThat(provider.getClientType(token))
                    .isEqualTo(JwtTokenProvider.ClientType.APP);
        }

        @Test
        @DisplayName("MINIPROGRAM 端 Token 包含 clientType=MINIPROGRAM")
        void miniprogramToken_containsClientType() {
            String token = provider.generateAccessToken(
                    USER_ID, B2C, MEMBER_PRO, JwtTokenProvider.ClientType.MINIPROGRAM);
            assertThat(provider.getClientType(token))
                    .isEqualTo(JwtTokenProvider.ClientType.MINIPROGRAM);
        }

        @Test
        @DisplayName("WEB 和 APP 的 Refresh Token 写入不同 Redis Key")
        void refreshToken_differentRedisKeyPerClient() {
            provider.generateRefreshToken(USER_ID, B2C, MEMBER_PRO, JwtTokenProvider.ClientType.WEB);
            provider.generateRefreshToken(USER_ID, B2C, MEMBER_PRO, JwtTokenProvider.ClientType.APP);

            // 两次写入的 key 应不同（含 :WEB 和 :APP 后缀）
            verify(valueOps, times(2)).set(argThat(key ->
                    key.contains(":WEB") || key.contains(":APP")),
                    anyString(), anyLong(), any());
        }

        @Test
        @DisplayName("ClientType.fromCode 未知值返回 WEB 默认")
        void clientType_unknownCodeDefaultsToWeb() {
            assertThat(JwtTokenProvider.ClientType.fromCode("UNKNOWN"))
                    .isEqualTo(JwtTokenProvider.ClientType.WEB);
            assertThat(JwtTokenProvider.ClientType.fromCode(null))
                    .isEqualTo(JwtTokenProvider.ClientType.WEB);
        }
    }

    // ================================================================
    //  自定义过期时间
    // ================================================================

    @Nested
    @DisplayName("自定义过期时间")
    class CustomExpirationTests {

        @Test
        @DisplayName("自定义过期时间 1h 的 Access Token 可正常解析")
        void customExpiration_1hour() {
            long oneHour = 3_600_000L;
            String token = provider.generateAccessToken(
                    USER_ID, B2C, MEMBER_PRO, JwtTokenProvider.ClientType.WEB, oneHour);
            // Token 在1h内有效，应能正常解析
            Claims claims = provider.parseToken(token);
            assertThat(claims.getSubject()).isEqualTo(USER_ID);
        }

        @Test
        @DisplayName("自定义过期时间 1ms（立即过期）Token 解析抛 TOKEN_EXPIRED")
        void customExpiration_immediateExpiry() throws InterruptedException {
            String token = provider.generateAccessToken(
                    USER_ID, B2C, MEMBER_PRO, JwtTokenProvider.ClientType.WEB, 1L);
            Thread.sleep(10);  // 等待过期

            assertThatThrownBy(() -> provider.parseToken(token))
                    .isInstanceOf(BizException.class)
                    .satisfies(e ->
                            assertThat(((BizException) e).getCode())
                                    .isEqualTo(ResultCode.TOKEN_EXPIRED.getCode()));
        }

        @Test
        @DisplayName("自定义过期时间的 Token 对（Access 2h / Refresh 30d）")
        void tokenPair_customExpiration() {
            long access  = 7_200_000L;    // 2h
            long refresh = 2_592_000_000L; // 30d
            JwtTokenProvider.TokenPair pair = provider.generateTokenPair(
                    USER_ID, B2C, MEMBER_PRO, JwtTokenProvider.ClientType.WEB,
                    access, refresh);

            assertThat(pair.accessToken()).isNotBlank();
            assertThat(pair.refreshToken()).isNotBlank();
            assertThat(pair.accessTokenExpireMs()).isEqualTo(access);
            assertThat(pair.refreshTokenExpireMs()).isEqualTo(refresh);
        }
    }

    // ================================================================
    //  异常与安全
    // ================================================================

    @Nested
    @DisplayName("Token 异常与安全")
    class SecurityTests {

        @Test
        @DisplayName("篡改 Token 抛出 TOKEN_INVALID")
        void tamperedToken_throwsInvalid() {
            String token = provider.generateAccessToken(
                    USER_ID, B2C, MEMBER_PRO, JwtTokenProvider.ClientType.WEB);
            String tampered = token + "tampered";

            assertThatThrownBy(() -> provider.parseToken(tampered))
                    .isInstanceOf(BizException.class)
                    .satisfies(e ->
                            assertThat(((BizException) e).getCode())
                                    .isEqualTo(ResultCode.TOKEN_INVALID.getCode()));
        }

        @Test
        @DisplayName("过期 Token validateToken 返回 false")
        void expiredToken_validateReturnsFalse() throws InterruptedException {
            JwtProperties shortProps = new JwtProperties();
            shortProps.setSecret("ilbuy-test-secret-key-must-be-at-least-32-chars");
            shortProps.setExpiration(1L);
            shortProps.setEnableBlacklist(false);
            JwtTokenProvider shortProvider = new JwtTokenProvider(shortProps, redisTemplate);

            String token = shortProvider.generateAccessToken(
                    USER_ID, B2C, MEMBER_PRO, JwtTokenProvider.ClientType.WEB);
            Thread.sleep(10);

            assertThat(shortProvider.validateToken(token)).isFalse();
        }

        @Test
        @DisplayName("resolveToken 正确去除 Bearer 前缀")
        void resolveToken_stripsBearerPrefix() {
            String raw   = "some.jwt.token";
            String bearer = "Bearer " + raw;
            assertThat(provider.resolveToken(bearer)).isEqualTo(raw);
        }

        @Test
        @DisplayName("resolveToken null/无前缀 返回 null")
        void resolveToken_invalidInputReturnsNull() {
            assertThat(provider.resolveToken(null)).isNull();
            assertThat(provider.resolveToken("InvalidToken")).isNull();
        }
    }

    // ================================================================
    //  Refresh Token
    // ================================================================

    @Nested
    @DisplayName("Refresh Token 携带用户信息")
    class RefreshTokenTests {

        @Test
        @DisplayName("Refresh Token Claims 包含 userType / memberLevel / clientType")
        void refreshToken_containsUserInfo() {
            String refreshToken = provider.generateRefreshToken(
                    USER_ID, B2B, MEMBER_PRO, JwtTokenProvider.ClientType.APP);
            Claims claims = provider.parseToken(refreshToken);

            assertThat(claims.get("userType",    String.class)).isEqualTo(B2B);
            assertThat(claims.get("memberLevel", String.class)).isEqualTo(MEMBER_PRO);
            assertThat(claims.get("clientType",  String.class)).isEqualTo("APP");
            assertThat(claims.get("type",        String.class)).isEqualTo("refresh");
        }

        @Test
        @DisplayName("Token 对中 Refresh Token 也包含用户信息")
        void tokenPair_refreshContainsUserInfo() {
            JwtTokenProvider.TokenPair pair = provider.generateTokenPair(
                    USER_ID, B2C, MEMBER_PRO, JwtTokenProvider.ClientType.WEB);
            Claims claims = provider.parseToken(pair.refreshToken());

            assertThat(claims.get("userType",    String.class)).isEqualTo(B2C);
            assertThat(claims.get("memberLevel", String.class)).isEqualTo(MEMBER_PRO);
            assertThat(claims.get("clientType",  String.class)).isEqualTo("WEB");
        }
    }
}
