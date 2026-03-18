package com.ilbuy.common.openfeign.config;

import com.alibaba.cloud.sentinel.feign.SentinelFeignAutoConfiguration;
import com.alibaba.csp.sentinel.slots.block.BlockException;
import com.ilbuy.common.core.enums.ResultCode;
import com.ilbuy.common.core.exception.BizException;
import feign.Feign;
import feign.Target;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.AutoConfigureBefore;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Scope;

/**
 * Sentinel + OpenFeign 熔断降级配置
 *
 * <p>在 application.yml 中启用：</p>
 * <pre>
 * feign:
 *   sentinel:
 *     enabled: true
 *
 * spring:
 *   cloud:
 *     sentinel:
 *       eager: true              # 饥饿模式（启动即连接 Dashboard）
 *       transport:
 *         dashboard: sentinel-dashboard:8080
 *         port: 8719
 * </pre>
 *
 * <p>各微服务 Feign Client 配合 FallbackFactory 使用：</p>
 * <pre>{@code
 * @FeignClient(
 *     name = "user-service",
 *     fallbackFactory = UserFeignFallbackFactory.class
 * )
 * public interface UserFeignClient { ... }
 *
 * @Component
 * public class UserFeignFallbackFactory implements FallbackFactory<UserFeignClient> {
 *     @Override
 *     public UserFeignClient create(Throwable cause) {
 *         return id -> {
 *             if (cause instanceof BizException biz) throw biz;
 *             log.error("user-service getById fallback", cause);
 *             return Result.fail(ResultCode.SERVICE_UNAVAILABLE, "用户服务不可用");
 *         };
 *     }
 * }
 * }</pre>
 *
 * <p>Sentinel 流控规则（推荐通过 Nacos 动态推送）：</p>
 * <pre>
 * # Nacos Data ID: sentinel-flow-rules.json
 * [
 *   {"resource":"GET:/user/profile","limitApp":"default","grade":1,"count":100,"strategy":0},
 *   {"resource":"POST:/order/create","limitApp":"default","grade":1,"count":50,"strategy":0}
 * ]
 * </pre>
 */
@Slf4j
@Configuration
@ConditionalOnClass({SentinelFeignAutoConfiguration.class, Feign.class})
@ConditionalOnProperty(name = "feign.sentinel.enabled", havingValue = "true")
@AutoConfigureBefore(SentinelFeignAutoConfiguration.class)
public class SentinelFeignConfig {

    /**
     * Sentinel 感知的 Feign Builder（替换默认 Builder）
     *
     * <p>必须声明为 prototype scope，确保每个 FeignClient 独立实例化。</p>
     */
    @Bean
    @Scope("prototype")
    public Feign.Builder sentinelFeignBuilder() {
        log.info("[SentinelFeign] 启用 Sentinel 熔断降级");
        return com.alibaba.cloud.sentinel.feign.SentinelFeign.builder();
    }

    /**
     * 全局 BlockException 转 BizException 处理
     *
     * <p>Sentinel 触发流控/熔断时抛出 {@link BlockException}，
     * 此处统一转为业务异常，由 GlobalExceptionHandler 处理。</p>
     */
    public static void handleBlockException(String resourceName, BlockException ex) {
        log.warn("[Sentinel] 资源 {} 触发熔断/限流: {}", resourceName, ex.getClass().getSimpleName());
        throw new BizException(ResultCode.TOO_MANY_REQUESTS,
                "服务繁忙，请稍后重试 [" + resourceName + "]");
    }

    /**
     * Sentinel 资源名构建器（统一格式：HTTP_METHOD:PATH）
     */
    public static String buildResourceName(String method, String path) {
        return method.toUpperCase() + ":" + path;
    }

    /**
     * 自定义 Sentinel 日志输出路径（避免污染应用日志目录）
     */
    static {
        System.setProperty("csp.sentinel.log.dir", System.getProperty("user.home") + "/logs/sentinel/");
    }
}
