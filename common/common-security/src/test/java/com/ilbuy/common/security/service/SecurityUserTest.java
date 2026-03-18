package com.ilbuy.common.security.service;

import com.ilbuy.common.security.model.LoginUser;
import com.ilbuy.common.security.model.SecurityUser;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;

import java.util.List;

import static org.assertj.core.api.Assertions.*;

@DisplayName("SecurityUser 线程安全上下文工具测试")
class SecurityUserTest {

    private LoginUser loginUser;

    @BeforeEach
    void setUp() {
        loginUser = LoginUser.builder()
                .userId(500L)
                .username("admin")
                .roles(List.of("ROLE_ADMIN", "ROLE_USER"))
                .tenantId("tenant-xyz")
                .build();

        UsernamePasswordAuthenticationToken auth =
                new UsernamePasswordAuthenticationToken(loginUser, null, loginUser.getAuthorities());
        SecurityContextHolder.getContext().setAuthentication(auth);
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    @Test
    @DisplayName("getLoginUser 返回正确实体")
    void getLoginUser_returnsEntity() {
        LoginUser user = SecurityUser.getLoginUser();
        assertThat(user).isNotNull();
        assertThat(user.getUserId()).isEqualTo(500L);
        assertThat(user.getUsername()).isEqualTo("admin");
    }

    @Test
    @DisplayName("getUserId 返回正确 ID")
    void getUserId_correct() {
        assertThat(SecurityUser.getUserId()).isEqualTo(500L);
    }

    @Test
    @DisplayName("getUsername 返回正确用户名")
    void getUsername_correct() {
        assertThat(SecurityUser.getUsername()).isEqualTo("admin");
    }

    @Test
    @DisplayName("getTenantId 返回正确租户 ID")
    void getTenantId_correct() {
        assertThat(SecurityUser.getTenantId()).isEqualTo("tenant-xyz");
    }

    @Test
    @DisplayName("hasRole(ROLE_ADMIN) 返回 true")
    void hasRole_existingRole() {
        assertThat(SecurityUser.hasRole("ROLE_ADMIN")).isTrue();
    }

    @Test
    @DisplayName("hasRole(ROLE_GUEST) 返回 false")
    void hasRole_missingRole() {
        assertThat(SecurityUser.hasRole("ROLE_GUEST")).isFalse();
    }

    @Test
    @DisplayName("isAuthenticated 已认证返回 true")
    void isAuthenticated_true() {
        assertThat(SecurityUser.isAuthenticated()).isTrue();
    }

    @Test
    @DisplayName("未认证时 isAuthenticated 返回 false")
    void isAuthenticated_false_whenNoContext() {
        SecurityContextHolder.clearContext();
        assertThat(SecurityUser.isAuthenticated()).isFalse();
    }

    @Test
    @DisplayName("未认证时 getUserId 返回 null")
    void getUserId_null_whenNoContext() {
        SecurityContextHolder.clearContext();
        assertThat(SecurityUser.getUserId()).isNull();
    }
}
