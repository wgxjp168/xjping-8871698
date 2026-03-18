package com.ilbuy.common.security.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

import java.io.Serial;
import java.util.Collection;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 登录用户信息（Spring Security UserDetails 实现）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LoginUser implements UserDetails {

    @Serial
    private static final long serialVersionUID = 1L;

    /** 用户 ID */
    private Long userId;

    /** 用户名 */
    private String username;

    /** 密码（序列化时忽略） */
    @JsonIgnore
    private String password;

    /** 邮箱 */
    private String email;

    /** 手机号 */
    private String mobile;

    /** 租户 ID */
    private String tenantId;

    /** 角色列表（如 ROLE_ADMIN, ROLE_USER） */
    private List<String> roles;

    /** 权限列表（如 user:list, order:create） */
    private List<String> permissions;

    /** 账号是否启用 */
    @Builder.Default
    private boolean enabled = true;

    /** 账号是否未锁定 */
    @Builder.Default
    private boolean accountNonLocked = true;

    /** Token（登录后填充） */
    private String accessToken;

    /** Refresh Token */
    private String refreshToken;

    // ──────────────────── UserDetails ────────────────────

    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        if (roles == null || roles.isEmpty()) return List.of();
        return roles.stream()
                .map(SimpleGrantedAuthority::new)
                .collect(Collectors.toList());
    }

    @Override
    @JsonIgnore
    public String getPassword() {
        return password;
    }

    @Override
    public String getUsername() {
        return username;
    }

    @Override
    public boolean isAccountNonExpired() {
        return true;
    }

    @Override
    public boolean isAccountNonLocked() {
        return accountNonLocked;
    }

    @Override
    public boolean isCredentialsNonExpired() {
        return true;
    }

    @Override
    public boolean isEnabled() {
        return enabled;
    }
}
