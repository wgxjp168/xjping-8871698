package com.ilbuy.common.openfeign.fallback;

import com.ilbuy.common.core.enums.ResultCode;
import com.ilbuy.common.core.exception.BizException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.openfeign.FallbackFactory;

import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * 通用 Feign Fallback 工厂
 *
 * <p>为 Feign Client 提供默认降级实现：所有方法抛出 {@link BizException}（SERVICE_UNAVAILABLE），
 * 业务层可通过全局异常处理器统一响应 503。</p>
 *
 * <p>用法一：注册全局默认 Fallback（推荐在网关聚合层使用）</p>
 * <pre>{@code
 * @FeignClient(
 *     name = "user-service",
 *     fallbackFactory = DefaultFallbackFactory.class
 * )
 * public interface UserFeignClient { ... }
 * }</pre>
 *
 * <p>用法二：各业务客户端自定义 FallbackFactory（推荐）</p>
 * <pre>{@code
 * @Component
 * public class UserFeignFallbackFactory implements FallbackFactory<UserFeignClient> {
 *     @Override
 *     public UserFeignClient create(Throwable cause) {
 *         return new UserFeignClient() {
 *             public Result<UserVO> getById(Long id) {
 *                 log.error("user-service getById fallback, cause={}", cause.getMessage());
 *                 return Result.fail(ResultCode.SERVICE_UNAVAILABLE, "用户服务不可用");
 *             }
 *         };
 *     }
 * }
 * }</pre>
 */
@Slf4j
public class DefaultFallbackFactory<T> implements FallbackFactory<T> {

    private final Class<T> targetType;

    public DefaultFallbackFactory(Class<T> targetType) {
        this.targetType = targetType;
    }

    @Override
    @SuppressWarnings("unchecked")
    public T create(Throwable cause) {
        log.error("[DefaultFallback] Feign 降级触发 target={} cause={}",
                targetType.getSimpleName(), cause.getMessage());

        return (T) Proxy.newProxyInstance(
                targetType.getClassLoader(),
                new Class[]{targetType},
                new FallbackHandler(cause, targetType.getSimpleName())
        );
    }

    /**
     * 降级处理器：任何调用都抛 BizException
     */
    private record FallbackHandler(Throwable cause, String serviceName)
            implements InvocationHandler {

        @Override
        public Object invoke(Object proxy, Method method, Object[] args) {
            log.warn("[DefaultFallback] {}.{}() 触发熔断降级，原因：{}",
                    serviceName, method.getName(), cause.getMessage());
            throw new BizException(ResultCode.SERVICE_UNAVAILABLE,
                    serviceName + " 服务暂时不可用，请稍后重试");
        }
    }
}
