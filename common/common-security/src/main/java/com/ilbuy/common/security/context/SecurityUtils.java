package com.ilbuy.common.security.context;

import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.common.core.result.ResultCode;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;

import java.util.Optional;

/**
 * Security 上下文工具类
 *
 * <p>在Controller/Service中便捷获取当前登录用户信息：
 * <pre>{@code
 * // 获取当前用户ID
 * Long userId = SecurityUtils.currentUserId();
 *
 * // 获取当前用户（完整信息）
 * LoginUser user = SecurityUtils.currentUser();
 *
 * // 判断是否已登录
 * boolean loggedIn = SecurityUtils.isAuthenticated();
 * }</pre>
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
public final class SecurityUtils {

    private SecurityUtils() {}

    /**
     * 获取当前登录用户（可能为null）
     */
    public static LoginUser currentUserOrNull() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !authentication.isAuthenticated()) {
            return null;
        }
        Object principal = authentication.getPrincipal();
        if (principal instanceof LoginUser loginUser) {
            return loginUser;
        }
        return null;
    }

    /**
     * 获取当前登录用户（不为null，未登录则抛出异常）
     *
     * @throws BizException 未登录时抛出 UNAUTHORIZED
     */
    public static LoginUser currentUser() {
        return Optional.ofNullable(currentUserOrNull())
                .orElseThrow(BizException::unauthorized);
    }

    /**
     * 获取当前登录用户ID
     *
     * @throws BizException 未登录时抛出
     */
    public static Long currentUserId() {
        return currentUser().getUserId();
    }

    /**
     * 获取当前用户类型（B2B/B2C）
     */
    public static String currentUserType() {
        return currentUser().getUserType();
    }

    /**
     * 判断当前请求是否已认证
     */
    public static boolean isAuthenticated() {
        return currentUserOrNull() != null;
    }

    /**
     * 判断当前用户是否为B2B企业用户
     */
    public static boolean isB2BUser() {
        LoginUser user = currentUserOrNull();
        return user != null && user.isB2B();
    }

    /**
     * 判断当前用户是否为付费会员
     */
    public static boolean isPaidMember() {
        LoginUser user = currentUserOrNull();
        return user != null && user.isPaidMember();
    }
}
