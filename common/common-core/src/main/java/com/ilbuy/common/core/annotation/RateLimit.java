package com.ilbuy.common.core.annotation;

import java.lang.annotation.*;
import java.util.concurrent.TimeUnit;

/**
 * 接口限流注解
 * <p>配合 AOP + Redis lua 脚本实现滑动窗口限流</p>
 *
 * <pre>{@code
 * @GetMapping("/product/list")
 * @RateLimit(count = 100, period = 1, timeUnit = TimeUnit.MINUTES, message = "访问过于频繁")
 * public Result<PageResult<ProductVO>> list(...) { ... }
 * }</pre>
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface RateLimit {

    /**
     * 限流 Key 前缀（留空则使用方法全限定名）
     */
    String key() default "";

    /**
     * 时间窗口内最大允许请求数
     */
    long count() default 100L;

    /**
     * 时间窗口大小，默认 1
     */
    long period() default 1L;

    /**
     * 时间单位，默认分钟
     */
    TimeUnit timeUnit() default TimeUnit.MINUTES;

    /**
     * 触发限流时的提示消息
     */
    String message() default "请求过于频繁，请稍后重试";

    /**
     * 是否按用户 IP 限流（true=IP维度, false=全局维度）
     */
    boolean limitByIp() default true;
}
