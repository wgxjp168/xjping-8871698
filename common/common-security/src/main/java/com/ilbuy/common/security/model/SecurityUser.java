package com.ilbuy.common.security.model;

import com.ilbuy.common.core.constants.CommonConstants;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;

/**
 * 安全上下文工具类（获取当前登录用户）
 *
 * <pre>{@code
 * Long userId   = SecurityUser.getUserId();
 * String name   = SecurityUser.getUsername();
 * LoginUser user = SecurityUser.getLoginUser();
 * }</pre>
 */
public final class SecurityUser {

    private SecurityUser() {}

    /**
     * 获取当前认证信息
     */
    public static Authentication getAuthentication() {
        return SecurityContextHolder.getContext().getAuthentication();
    }

    /**
     * 获取当前登录用户
     *
     * @throws IllegalStateException 若未认证
     */
    public static LoginUser getLoginUser() {
        Authentication auth = getAuthentication();
        if (auth == null || !(auth.getPrincipal() instanceof LoginUser)) {
            throw new IllegalStateException("当前请求未认证");
        }
        return (LoginUser) auth.getPrincipal();
    }

    /**
     * 获取当前登录用户（未认证返回 null，不抛异常）
     */
    public static LoginUser getLoginUserOrNull() {
        Authentication auth = getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof LoginUser lu) return lu;
        return null;
    }

    /**
     * 获取当前用户 ID（未认证返回 null）
     */
    public static Long getUserId() {
        LoginUser u = getLoginUserOrNull();
        return u != null ? u.getUserId() : null;
    }

    /**
     * 获取当前用户名（未认证返回 null）
     */
    public static String getUsername() {
        LoginUser u = getLoginUserOrNull();
        return u != null ? u.getUsername() : null;
    }

    /**
     * 获取当前租户 ID（未认证返回 null）
     */
    public static String getTenantId() {
        LoginUser u = getLoginUserOrNull();
        return u != null ? u.getTenantId() : null;
    }

    /**
     * 判断是否已认证
     */
    public static boolean isAuthenticated() {
        Authentication auth = getAuthentication();
        return auth != null && auth.isAuthenticated()
                && !(auth.getPrincipal() instanceof String);
    }

    /**
     * 判断当前用户是否拥有指定角色
     */
    public static boolean hasRole(String role) {
        if (!isAuthenticated()) return false;
        return getAuthentication().getAuthorities().stream()
                .anyMatch(a -> a.getAuthority().equals(role));
    }

    /**
     * 从请求头提取用户 ID（网关注入场景，无 Spring Security 上下文时使用）
     */
    public static Long getUserIdFromHeader(jakarta.servlet.http.HttpServletRequest request) {
        String userIdStr = request.getHeader(CommonConstants.HEADER_USER_ID);
        if (userIdStr != null && !userIdStr.isBlank()) {
            try {
                return Long.parseLong(userIdStr);
            } catch (NumberFormatException ignored) {}
        }
        return null;
    }
}
