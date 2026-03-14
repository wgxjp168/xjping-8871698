package com.ilbuy.common.openfeign.fallback;

import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.common.core.result.Result;
import com.ilbuy.common.core.result.ResultCode;
import lombok.extern.slf4j.Slf4j;

/**
 * Feign 熔断降级基础类
 *
 * <p>各服务 FallbackFactory 继承此类，提供公共的降级处理方法。
 *
 * <p>使用示例：
 * <pre>{@code
 * @Component
 * public class UserFeignFallbackFactory
 *         extends BaseFallbackFactory<UserFeignClient>
 *         implements FallbackFactory<UserFeignClient> {
 *
 *     @Override
 *     public UserFeignClient create(Throwable cause) {
 *         return new UserFeignClient() {
 *             @Override
 *             public Result<UserVO> getUserInfo(Long userId) {
 *                 return fallbackResult(cause, "getUserInfo");
 *             }
 *         };
 *     }
 * }
 * }</pre>
 *
 * @param <T> Feign客户端接口类型
 * @author ILbuy Team
 * @version 1.0.0
 */
@Slf4j
public abstract class BaseFallbackFactory<T> {

    /**
     * 记录降级日志并返回标准降级响应
     *
     * @param cause      触发降级的异常
     * @param methodName 降级的方法名
     * @return 降级Result响应
     */
    protected <R> Result<R> fallbackResult(Throwable cause, String methodName) {
        logFallback(cause, methodName);
        if (cause instanceof BizException bizEx) {
            return Result.fail(bizEx.getCode(), bizEx.getMessage());
        }
        return Result.fail(ResultCode.SERVICE_UNAVAILABLE);
    }

    /**
     * 记录降级日志
     *
     * @param cause      异常
     * @param methodName 方法名
     */
    protected void logFallback(Throwable cause, String methodName) {
        if (cause instanceof BizException) {
            log.warn("[Fallback] 服务降级（业务异常）: method={}, cause={}", methodName, cause.getMessage());
        } else {
            log.error("[Fallback] 服务降级（系统异常）: method={}, error={}", methodName, cause.getMessage(), cause);
        }
    }

    /**
     * 判断是否为熔断触发的降级（而非业务异常导致的降级）
     *
     * @param cause 异常
     * @return true-熔断触发
     */
    protected boolean isCircuitBreakerOpen(Throwable cause) {
        return cause != null &&
                cause.getClass().getSimpleName().contains("CallNotPermittedException");
    }
}
