package com.ilbuy.common.core.aspect;

import com.ilbuy.common.core.annotation.RateLimit;
import com.ilbuy.common.core.enums.ResultCode;
import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.common.core.utils.IpUtils;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Before;
import org.aspectj.lang.reflect.MethodSignature;
import org.springframework.core.annotation.Order;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.lang.reflect.Method;
import java.time.Duration;
import java.util.Collections;
import java.util.List;

/**
 * 接口限流 AOP 切面（基于 Redis 滑动窗口算法）
 *
 * <p>算法原理：使用 Redis 有序集合（ZSET）实现滑动窗口，
 * 每次请求以当前时间戳为 score 写入一个成员，
 * 统计窗口内的请求数量，超限则拒绝。</p>
 *
 * <pre>{@code
 * @GetMapping("/product/list")
 * @RateLimit(count = 100, period = 1, timeUnit = TimeUnit.MINUTES)
 * public Result<PageResult<ProductVO>> list(...) { ... }
 *
 * // 全局维度（不区分 IP）
 * @RateLimit(count = 10, period = 1, timeUnit = TimeUnit.SECONDS, limitByIp = false)
 * public Result<Void> sendSms(...) { ... }
 * }</pre>
 */
@Slf4j
@Aspect
@Component
@Order(1)
@RequiredArgsConstructor
public class RateLimitAspect {

    private final StringRedisTemplate redisTemplate;

    /**
     * 滑动窗口限流 Lua 脚本（原子性保证）
     *
     * <p>逻辑：
     * <ol>
     *   <li>移除窗口外的过期成员（score < now - windowMs）</li>
     *   <li>统计当前窗口内请求数</li>
     *   <li>超过阈值返回 0（拒绝），否则添加当前请求并返回 1（允许）</li>
     * </ol>
     * </p>
     */
    private static final String SLIDING_WINDOW_SCRIPT =
            "local key = KEYS[1]\n" +
            "local now = tonumber(ARGV[1])\n" +
            "local window = tonumber(ARGV[2])\n" +
            "local limit = tonumber(ARGV[3])\n" +
            "local expire = tonumber(ARGV[4])\n" +
            // 移除窗口外过期成员
            "redis.call('ZREMRANGEBYSCORE', key, 0, now - window)\n" +
            // 统计当前窗口请求数
            "local count = redis.call('ZCARD', key)\n" +
            "if count >= limit then\n" +
            "    return 0\n" +
            "end\n" +
            // 添加当前请求（member = now + random，避免 score 重复）
            "redis.call('ZADD', key, now, now .. '-' .. math.random(100000))\n" +
            "redis.call('PEXPIRE', key, expire)\n" +
            "return 1";

    private final DefaultRedisScript<Long> slidingWindowScript =
            new DefaultRedisScript<>(SLIDING_WINDOW_SCRIPT, Long.class);

    @Before("@annotation(rateLimit)")
    public void doBefore(JoinPoint joinPoint, RateLimit rateLimit) {
        String key        = buildKey(joinPoint, rateLimit);
        long windowMs     = rateLimit.timeUnit().toMillis(rateLimit.period());
        long nowMs        = System.currentTimeMillis();
        long expireMs     = windowMs * 2; // 过期时间 = 2 倍窗口（防止 key 提前消失）

        Long result = redisTemplate.execute(
                slidingWindowScript,
                Collections.singletonList(key),
                String.valueOf(nowMs),
                String.valueOf(windowMs),
                String.valueOf(rateLimit.count()),
                String.valueOf(expireMs)
        );

        if (result == null || result == 0L) {
            log.warn("[RateLimit] 触发限流 key={} count={} window={}ms",
                    key, rateLimit.count(), windowMs);
            throw new BizException(ResultCode.TOO_MANY_REQUESTS, rateLimit.message());
        }

        log.debug("[RateLimit] 通过 key={}", key);
    }

    private String buildKey(JoinPoint joinPoint, RateLimit rateLimit) {
        MethodSignature sig  = (MethodSignature) joinPoint.getSignature();
        Method method        = sig.getMethod();
        String methodKey     = rateLimit.key().isBlank()
                ? method.getDeclaringClass().getName() + "#" + method.getName()
                : rateLimit.key();

        if (rateLimit.limitByIp()) {
            String ip = resolveClientIp();
            return "ilbuy:rate:" + methodKey + ":" + ip;
        }
        return "ilbuy:rate:" + methodKey;
    }

    private String resolveClientIp() {
        try {
            ServletRequestAttributes attrs =
                    (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attrs != null) {
                HttpServletRequest request = attrs.getRequest();
                return IpUtils.getRealIp(request);
            }
        } catch (Exception e) {
            log.debug("[RateLimit] 无法获取客户端 IP: {}", e.getMessage());
        }
        return "unknown";
    }
}
