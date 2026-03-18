package com.ilbuy.common.core.annotation;

import java.lang.annotation.*;
import java.util.concurrent.TimeUnit;

/**
 * 防重复提交注解
 * <p>配合 AOP 拦截器使用，基于 Redis 实现幂等</p>
 *
 * <pre>{@code
 * @PostMapping("/order/create")
 * @NoRepeatSubmit(interval = 5, message = "请勿重复下单")
 * public Result<Long> createOrder(@RequestBody OrderCreateDTO dto) { ... }
 * }</pre>
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface NoRepeatSubmit {

    /**
     * 间隔时间，默认 5 秒
     */
    long interval() default 5L;

    /**
     * 时间单位，默认秒
     */
    TimeUnit timeUnit() default TimeUnit.SECONDS;

    /**
     * 提示消息
     */
    String message() default "请勿重复操作，请稍后再试";
}
