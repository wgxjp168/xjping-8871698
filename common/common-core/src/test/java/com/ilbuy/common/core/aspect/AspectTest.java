package com.ilbuy.common.core.aspect;

import com.ilbuy.common.core.annotation.NoRepeatSubmit;
import com.ilbuy.common.core.annotation.RateLimit;
import com.ilbuy.common.core.enums.ResultCode;
import com.ilbuy.common.core.exception.BizException;
import org.junit.jupiter.api.Nested;
import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.reflect.MethodSignature;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.data.redis.core.script.RedisScript;

import java.lang.reflect.Method;
import java.time.Duration;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@DisplayName("AOP 切面单元测试")
@ExtendWith(MockitoExtension.class)
class AspectTest {

    @Mock StringRedisTemplate redisTemplate;
    @Mock ValueOperations<String, String> valueOps;
    @Mock JoinPoint joinPoint;
    @Mock MethodSignature methodSignature;

    @BeforeEach
    void setupMocks() throws NoSuchMethodException {
        when(joinPoint.getSignature()).thenReturn(methodSignature);
        when(methodSignature.getMethod()).thenReturn(
                TestService.class.getMethod("rateLimitedMethod"));
        when(methodSignature.getDeclaringTypeName()).thenReturn("TestService");
        when(methodSignature.getName()).thenReturn("rateLimitedMethod");
        when(joinPoint.getArgs()).thenReturn(new Object[]{});
    }

    // ═══════════════ RateLimitAspect ═══════════════

    @Nested
    @DisplayName("RateLimitAspect")
    class RateLimitAspectTests {

        private RateLimitAspect aspect;
        private RateLimit rateLimit;

        @BeforeEach
        void setUp() throws NoSuchMethodException {
            aspect     = new RateLimitAspect(redisTemplate);
            rateLimit  = TestService.class.getMethod("rateLimitedMethod")
                    .getAnnotation(RateLimit.class);
        }

        @Test
        @DisplayName("Redis 返回 1（允许） → 请求通过")
        void allowed_passes() {
            when(redisTemplate.execute(any(RedisScript.class), anyList(), any()))
                    .thenReturn(1L);

            assertThatNoException().isThrownBy(
                    () -> aspect.doBefore(joinPoint, rateLimit));
        }

        @Test
        @DisplayName("Redis 返回 0（超限） → 抛 BizException(TOO_MANY_REQUESTS)")
        void exceeded_throws() {
            when(redisTemplate.execute(any(RedisScript.class), anyList(), any()))
                    .thenReturn(0L);

            assertThatThrownBy(() -> aspect.doBefore(joinPoint, rateLimit))
                    .isInstanceOf(BizException.class)
                    .satisfies(e -> assertThat(((BizException) e).getCode())
                            .isEqualTo(ResultCode.TOO_MANY_REQUESTS.getCode()));
        }

        @Test
        @DisplayName("Redis 返回 null（异常情况） → 抛 BizException")
        void nullResult_throws() {
            when(redisTemplate.execute(any(RedisScript.class), anyList(), any()))
                    .thenReturn(null);

            assertThatThrownBy(() -> aspect.doBefore(joinPoint, rateLimit))
                    .isInstanceOf(BizException.class);
        }
    }

    // ═══════════════ NoRepeatSubmitAspect ═══════════════

    @Nested
    @DisplayName("NoRepeatSubmitAspect")
    class NoRepeatSubmitAspectTests {

        private NoRepeatSubmitAspect aspect;
        private NoRepeatSubmit annotation;

        @BeforeEach
        void setUp() throws NoSuchMethodException {
            aspect     = new NoRepeatSubmitAspect(redisTemplate);
            annotation = TestService.class.getMethod("idempotentMethod")
                    .getAnnotation(NoRepeatSubmit.class);
            when(joinPoint.getSignature()).thenReturn(methodSignature);
            when(methodSignature.getDeclaringTypeName()).thenReturn("TestService");
            when(methodSignature.getName()).thenReturn("idempotentMethod");
        }

        @Test
        @DisplayName("首次提交加锁成功 → 请求通过")
        void firstSubmit_passes() {
            when(redisTemplate.opsForValue()).thenReturn(valueOps);
            when(valueOps.setIfAbsent(anyString(), anyString(), any(Duration.class)))
                    .thenReturn(Boolean.TRUE);

            assertThatNoException().isThrownBy(
                    () -> aspect.doBefore(joinPoint, annotation));
        }

        @Test
        @DisplayName("重复提交加锁失败 → 抛 BizException(TOO_MANY_REQUESTS)")
        void repeatSubmit_throws() {
            when(redisTemplate.opsForValue()).thenReturn(valueOps);
            when(valueOps.setIfAbsent(anyString(), anyString(), any(Duration.class)))
                    .thenReturn(Boolean.FALSE);

            assertThatThrownBy(() -> aspect.doBefore(joinPoint, annotation))
                    .isInstanceOf(BizException.class)
                    .satisfies(e -> assertThat(((BizException) e).getCode())
                            .isEqualTo(ResultCode.TOO_MANY_REQUESTS.getCode()));
        }

        @Test
        @DisplayName("方法返回后释放锁（Redis delete 被调用）")
        void afterReturn_releasesLock() {
            when(redisTemplate.opsForValue()).thenReturn(valueOps);
            when(valueOps.setIfAbsent(anyString(), anyString(), any(Duration.class)))
                    .thenReturn(Boolean.TRUE);
            when(redisTemplate.delete(anyString())).thenReturn(true);

            aspect.doBefore(joinPoint, annotation);
            aspect.afterReturning();

            verify(redisTemplate, times(1)).delete(anyString());
        }

        @Test
        @DisplayName("方法抛异常后也释放锁")
        void afterThrowing_releasesLock() {
            when(redisTemplate.opsForValue()).thenReturn(valueOps);
            when(valueOps.setIfAbsent(anyString(), anyString(), any(Duration.class)))
                    .thenReturn(Boolean.TRUE);
            when(redisTemplate.delete(anyString())).thenReturn(true);

            aspect.doBefore(joinPoint, annotation);
            aspect.afterThrowing();

            verify(redisTemplate, times(1)).delete(anyString());
        }
    }

    // ═══════════════ 测试用 Service ═══════════════

    static class TestService {

        @RateLimit(count = 5, period = 1, timeUnit = TimeUnit.MINUTES, message = "访问过快")
        public void rateLimitedMethod() {}

        @NoRepeatSubmit(interval = 3, message = "请勿重复提交")
        public void idempotentMethod() {}
    }
}
