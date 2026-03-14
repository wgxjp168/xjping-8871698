package com.ilbuy.common.security.context;

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

/**
 * 登录用户信息（Security上下文存储的用户实体）
 *
 * <p>实现 Spring Security 的 UserDetails 接口，存储在 SecurityContext 中。
 * 在 Controller/Service 中通过 SecurityUtils.currentUser() 获取。
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LoginUser implements UserDetails {

    @Serial
    private static final long serialVersionUID = 1L;

    /** 用户ID */
    private Long userId;

    /** 用户名 */
    private String username;

    /** 用户类型：B2B/B2C */
    private String userType;

    /** 会员等级：FREE/BASIC/PRO/ENTERPRISE */
    private String memberLevel;

    /** 用户状态 */
    private boolean enabled;

    /** 当前JWT Token（用于登出时加入黑名单）*/
    private String currentToken;

    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        // 角色权限：ROLE_B2B / ROLE_B2C
        return List.of(new SimpleGrantedAuthority("ROLE_" + userType));
    }

    @Override
    public String getPassword() {
        return null;  // JWT模式下不需要密码
    }

    @Override
    public boolean isAccountNonExpired() {
        return true;
    }

    @Override
    public boolean isAccountNonLocked() {
        return enabled;
    }

    @Override
    public boolean isCredentialsNonExpired() {
        return true;
    }

    @Override
    public boolean isEnabled() {
        return enabled;
    }

    /**
     * 判断是否为B2B企业用户
     */
    public boolean isB2B() {
        return "B2B".equalsIgnoreCase(userType);
    }

    /**
     * 判断是否为B2C个人用户
     */
    public boolean isB2C() {
        return "B2C".equalsIgnoreCase(userType);
    }

    /**
     * 判断是否为付费会员
     */
    public boolean isPaidMember() {
        return !"FREE".equalsIgnoreCase(memberLevel);
    }
}
