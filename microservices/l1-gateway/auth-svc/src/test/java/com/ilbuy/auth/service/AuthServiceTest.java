package com.ilbuy.auth.service;

import com.ilbuy.auth.config.JwtProperties;
import com.ilbuy.auth.dto.LoginRequest;
import com.ilbuy.auth.dto.LoginResponse;
import com.ilbuy.auth.dto.TokenIntrospectResponse;
import com.ilbuy.auth.dto.TokenRefreshRequest;
import com.ilbuy.auth.entity.UserCredential;
import com.ilbuy.auth.mapper.UserCredentialMapper;
import com.ilbuy.auth.service.impl.AuthServiceImpl;
import com.ilbuy.auth.util.JwtUtils;
import com.ilbuy.common.core.exception.BizException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.Duration;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * AuthService 单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("AuthService 单元测试")
class AuthServiceTest {

    @Mock
    private UserCredentialMapper credentialMapper;

    @Mock
    private StringRedisTemplate redisTemplate;

    @Mock
    private ValueOperations<String, String> valueOperations;

    private PasswordEncoder passwordEncoder;
    private JwtUtils jwtUtils;
    private JwtProperties jwtProperties;

    @InjectMocks
    private AuthServiceImpl authService;

    private static final String RAW_PASSWORD = "Test@123456";
    private static final String SECRET = "ilbuy-platform-jwt-secret-key-2024-must-be-at-least-256-bits";

    @BeforeEach
    void setUp() {
        passwordEncoder = new BCryptPasswordEncoder(4); // 快速hash，仅测试用
        jwtProperties = new JwtProperties();
        jwtProperties.setSecret(SECRET);
        jwtProperties.setAccessTokenTtl(7200);
        jwtProperties.setRefreshTokenTtl(604800);

        jwtUtils = new JwtUtils(jwtProperties);

        ReflectionTestUtils.setField(authService, "passwordEncoder", passwordEncoder);
        ReflectionTestUtils.setField(authService, "jwtUtils", jwtUtils);
        ReflectionTestUtils.setField(authService, "jwtProperties", jwtProperties);

        lenient().when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        lenient().doNothing().when(valueOperations).set(anyString(), anyString(), any(Duration.class));
    }

    @Test
    @DisplayName("正常登录 - 返回有效 Token")
    void login_success() {
        UserCredential credential = buildCredential("CONSUMER", "ROLE_USER");
        when(credentialMapper.findByLoginId("consumer@test.com")).thenReturn(credential);

        LoginRequest request = new LoginRequest();
        request.setLoginId("consumer@test.com");
        request.setPassword(RAW_PASSWORD);

        LoginResponse response = authService.login(request);

        assertThat(response.getAccessToken()).isNotBlank();
        assertThat(response.getRefreshToken()).isNotBlank();
        assertThat(response.getUserType()).isEqualTo("CONSUMER");
        assertThat(response.getTokenType()).isEqualTo("Bearer");
    }

    @Test
    @DisplayName("用户不存在 - 抛出 BizException")
    void login_userNotFound() {
        when(credentialMapper.findByLoginId(anyString())).thenReturn(null);

        LoginRequest request = new LoginRequest();
        request.setLoginId("notexist@test.com");
        request.setPassword(RAW_PASSWORD);

        assertThatThrownBy(() -> authService.login(request))
            .isInstanceOf(BizException.class);
    }

    @Test
    @DisplayName("密码错误 - 抛出 BizException")
    void login_wrongPassword() {
        UserCredential credential = buildCredential("CONSUMER", "ROLE_USER");
        when(credentialMapper.findByLoginId(anyString())).thenReturn(credential);

        LoginRequest request = new LoginRequest();
        request.setLoginId("consumer@test.com");
        request.setPassword("WrongPassword");

        assertThatThrownBy(() -> authService.login(request))
            .isInstanceOf(BizException.class);
    }

    @Test
    @DisplayName("账号被禁用 - 抛出 BizException")
    void login_disabledAccount() {
        UserCredential credential = buildCredential("CONSUMER", "ROLE_USER");
        credential.setEnabled(0);
        when(credentialMapper.findByLoginId(anyString())).thenReturn(credential);

        LoginRequest request = new LoginRequest();
        request.setLoginId("consumer@test.com");
        request.setPassword(RAW_PASSWORD);

        assertThatThrownBy(() -> authService.login(request))
            .isInstanceOf(BizException.class);
    }

    @Test
    @DisplayName("Token 自省 - 有效 Token 返回用户信息")
    void introspect_validToken() {
        String token = jwtUtils.generateAccessToken("10001", "BUSINESS", "ROLE_ENTERPRISE");
        when(redisTemplate.hasKey(anyString())).thenReturn(false);

        TokenIntrospectResponse response = authService.introspect(token);

        assertThat(response.isActive()).isTrue();
        assertThat(response.getUserId()).isEqualTo("10001");
        assertThat(response.getUserType()).isEqualTo("BUSINESS");
    }

    @Test
    @DisplayName("Token 自省 - 黑名单 Token 返回 active=false")
    void introspect_blacklistedToken() {
        String token = jwtUtils.generateAccessToken("10001", "CONSUMER", "ROLE_USER");
        when(redisTemplate.hasKey(anyString())).thenReturn(true);

        TokenIntrospectResponse response = authService.introspect(token);

        assertThat(response.isActive()).isFalse();
    }

    // ============ 辅助方法 ============

    private UserCredential buildCredential(String userType, String roles) {
        UserCredential c = new UserCredential();
        c.setUserId(10001L);
        c.setUsername("consumer_test");
        c.setEmail("consumer@test.com");
        c.setPasswordHash(passwordEncoder.encode(RAW_PASSWORD));
        c.setUserType(userType);
        c.setRoles(roles);
        c.setEnabled(1);
        return c;
    }
}
