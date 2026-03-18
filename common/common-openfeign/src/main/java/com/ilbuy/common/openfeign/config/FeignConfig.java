package com.ilbuy.common.openfeign.config;

import com.ilbuy.common.openfeign.decoder.FeignErrorDecoder;
import com.ilbuy.common.openfeign.interceptor.FeignTokenRelayInterceptor;
import com.ilbuy.common.openfeign.interceptor.FeignTraceIdInterceptor;
import feign.Logger;
import feign.Request;
import feign.Retryer;
import feign.codec.ErrorDecoder;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.concurrent.TimeUnit;

/**
 * Feign 全局配置
 *
 * <p>配置项：
 * <ul>
 *   <li>连接超时 3s，读取超时 10s</li>
 *   <li>重试策略：间隔 100ms，最大 300ms，最多重试 3 次</li>
 *   <li>Token 透传拦截器</li>
 *   <li>统一错误解码器</li>
 *   <li>日志级别 FULL（生产可调为 BASIC）</li>
 * </ul>
 * </p>
 *
 * <p>全局生效方式（application.yml）：
 * <pre>
 * spring:
 *   cloud:
 *     openfeign:
 *       client:
 *         default-config: default
 *       sentinel:
 *         enabled: true
 * </pre>
 *
 * <p>单个 Client 覆盖日志（application.yml）：
 * <pre>
 * logging:
 *   level:
 *     com.ilbuy.l5.client.UserFeignClient: DEBUG
 * </pre>
 * </p>
 */
@Configuration
public class FeignConfig {

    /**
     * 请求超时配置（全局默认）
     * <ul>
     *   <li>connectTimeout: 3s</li>
     *   <li>readTimeout: 10s</li>
     * </ul>
     */
    @Bean
    @ConditionalOnMissingBean(Request.Options.class)
    public Request.Options requestOptions() {
        return new Request.Options(
                3_000, TimeUnit.MILLISECONDS,   // connectTimeout
                10_000, TimeUnit.MILLISECONDS,  // readTimeout
                true                            // 允许重定向
        );
    }

    /**
     * 重试策略：初始间隔 100ms，最大 300ms，最多 3 次
     * <p>注意：POST 请求默认不重试，需显式在 @FeignClient 配置</p>
     */
    @Bean
    @ConditionalOnMissingBean(Retryer.class)
    public Retryer retryer() {
        return new Retryer.Default(100L, 300L, 3);
    }

    /**
     * Token 透传拦截器（所有 Feign 请求自动注入）
     */
    @Bean
    public FeignTokenRelayInterceptor feignTokenRelayInterceptor() {
        return new FeignTokenRelayInterceptor();
    }

    /**
     * 链路追踪 ID 拦截器（传播 X-Trace-Id，对齐 MDC）
     */
    @Bean
    @ConditionalOnMissingBean(FeignTraceIdInterceptor.class)
    public FeignTraceIdInterceptor feignTraceIdInterceptor() {
        return new FeignTraceIdInterceptor();
    }

    /**
     * 错误解码器（统一转换 4xx/5xx 为 BizException）
     */
    @Bean
    @ConditionalOnMissingBean(ErrorDecoder.class)
    public ErrorDecoder errorDecoder() {
        return new FeignErrorDecoder();
    }

    /**
     * Feign 日志级别（FULL=记录 header/body，生产可改为 BASIC）
     */
    @Bean
    public Logger.Level feignLoggerLevel() {
        return Logger.Level.FULL;
    }
}
