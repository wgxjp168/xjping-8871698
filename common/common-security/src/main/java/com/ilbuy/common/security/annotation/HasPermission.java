package com.ilbuy.common.security.annotation;

import org.springframework.security.access.prepost.PreAuthorize;

import java.lang.annotation.*;

/**
 * 自定义权限注解（封装 @PreAuthorize，简化使用）
 *
 * <pre>{@code
 * // 等价于 @PreAuthorize("hasAuthority('user:list')")
 * @HasPermission("user:list")
 * public Result<List<UserVO>> list() { ... }
 * }</pre>
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
@PreAuthorize("hasAuthority('{value}')")
public @interface HasPermission {

    /**
     * 权限标识符，如 user:list, order:create
     */
    String value();
}
