package com.ilbuy.common.core.aspect;

import com.ilbuy.common.core.annotation.NoRepeatSubmit;
import com.ilbuy.common.core.enums.ResultCode;
import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.common.core.utils.EncryptUtils;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.annotation.AfterReturning;
import org.aspectj.lang.annotation.AfterThrowing;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Before;
import org.aspectj.lang.reflect.MethodSignature;
import org.springframework.core.annotation.Order;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.time.Duration;
import java.util.Arrays;

/**
 * 防重复提交 AOP 切面（基于 Redis SET NX 实现幂等锁）
 *
 * <p>锁 Key 构成：客户端 IP + 请求 URI + 请求参数摘要（MD5）</p>
 *
 * <p>生命周期：</p>
 * <ul>
 *   <li>请求进入 → 尝试获取锁（SET NX），失败则拒绝</li>
 *   <li>方法正常返回 → 释放锁（使业务可再次提交）</li>
 *   <li>方法抛异常 → 同样释放锁（允许用户修正后重试）</li>
 * </ul>
 *
 * <pre>{@code
 * @PostMapping("/order/create")
 * @NoRepeatSubmit(interval = 5, message = "请勿重复下单")
 * public Result<Long> createOrder(@RequestBody @Valid OrderCreateDTO dto) { ... }
 * }</pre>
 */
@Slf4j
@Aspect
@Component
@Order(2)
@RequiredArgsConstructor
public class NoRepeatSubmitAspect {

    private static final String LOCK_PREFIX = "ilbuy:no_repeat:";

    private final StringRedisTemplate redisTemplate;

    @Before("@annotation(noRepeatSubmit)")
    public void doBefore(JoinPoint joinPoint, NoRepeatSubmit noRepeatSubmit) {
        String lockKey = buildLockKey(joinPoint);

        // SET NX（不存在时设置）：返回 true 表示加锁成功
        Duration expire = Duration.of(noRepeatSubmit.interval(), toChronoUnit(noRepeatSubmit.timeUnit()));
        Boolean locked  = redisTemplate.opsForValue().setIfAbsent(lockKey, "1", expire);

        if (!Boolean.TRUE.equals(locked)) {
            log.warn("[NoRepeatSubmit] 重复提交拦截 key={}", lockKey);
            throw new BizException(ResultCode.TOO_MANY_REQUESTS, noRepeatSubmit.message());
        }

        log.debug("[NoRepeatSubmit] 加锁成功 key={} expire={}", lockKey, expire);
        // 将 key 存入当前线程（供 After 通知释放）
        LOCK_KEY_HOLDER.set(lockKey);
    }

    @AfterReturning("@annotation(com.ilbuy.common.core.annotation.NoRepeatSubmit)")
    public void afterReturning() {
        releaseLock();
    }

    @AfterThrowing("@annotation(com.ilbuy.common.core.annotation.NoRepeatSubmit)")
    public void afterThrowing() {
        // 业务异常时释放锁（允许用户修正后重试）
        releaseLock();
    }

    private void releaseLock() {
        String key = LOCK_KEY_HOLDER.get();
        if (key != null) {
            redisTemplate.delete(key);
            LOCK_KEY_HOLDER.remove();
            log.debug("[NoRepeatSubmit] 锁释放 key={}", key);
        }
    }

    private String buildLockKey(JoinPoint joinPoint) {
        MethodSignature sig = (MethodSignature) joinPoint.getSignature();
        String methodName   = sig.getDeclaringTypeName() + "#" + sig.getName();

        // 参数摘要（避免 key 过长）
        String paramHash = EncryptUtils.md5(Arrays.toString(joinPoint.getArgs()));

        // 尝试获取 HTTP 请求上下文
        String uri  = "unknown";
        String ip   = "unknown";
        try {
            ServletRequestAttributes attrs =
                    (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attrs != null) {
                HttpServletRequest request = attrs.getRequest();
                uri = request.getRequestURI();
                ip  = com.ilbuy.common.core.utils.IpUtils.getRealIp(request);
            }
        } catch (Exception ignored) {}

        return LOCK_PREFIX + EncryptUtils.md5(ip + ":" + uri + ":" + methodName + ":" + paramHash);
    }

    private java.time.temporal.ChronoUnit toChronoUnit(java.util.concurrent.TimeUnit timeUnit) {
        return switch (timeUnit) {
            case NANOSECONDS  -> java.time.temporal.ChronoUnit.NANOS;
            case MICROSECONDS -> java.time.temporal.ChronoUnit.MICROS;
            case MILLISECONDS -> java.time.temporal.ChronoUnit.MILLIS;
            case SECONDS      -> java.time.temporal.ChronoUnit.SECONDS;
            case MINUTES      -> java.time.temporal.ChronoUnit.MINUTES;
            case HOURS        -> java.time.temporal.ChronoUnit.HOURS;
            case DAYS         -> java.time.temporal.ChronoUnit.DAYS;
        };
    }

    /** 线程本地存储：持有当前请求的锁 Key */
    private static final ThreadLocal<String> LOCK_KEY_HOLDER = new ThreadLocal<>();
}
