package com.ilbuy.common.openfeign.config;

import com.ilbuy.common.openfeign.decoder.FeignErrorDecoder;
import com.ilbuy.common.openfeign.interceptor.FeignRequestInterceptor;
import feign.Logger;
import feign.Request;
import feign.Retryer;
import feign.codec.ErrorDecoder;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.cloud.openfeign.EnableFeignClients;
import org.springframework.context.annotation.Bean;

import java.util.concurrent.TimeUnit;

/**
 * OpenFeign 全局自动配置
 *
 * <p>配置项：
 * <ul>
 *   <li>连接超时：5秒</li>
 *   <li>读取超时：AI决策接口30秒，其余10秒</li>
 *   <li>重试策略：最多3次，间隔100ms起（指数增长）</li>
 *   <li>日志级别：dev=FULL，prod=BASIC</li>
 *   <li>请求拦截器：自动传递用户信息和TraceId</li>
 *   <li>错误解码器：统一错误处理</li>
 * </ul>
 *
 * <p>重试策略说明：
 * Feign默认重试用于幂等接口（GET/DELETE），
 * POST接口不建议自动重试（可能导致重复提交），
 * 非幂等接口需在各服务单独配置。
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@AutoConfiguration
public class FeignAutoConfiguration {

    /**
     * 请求选项：超时配置
     * AI决策接口需要较长时间（最多30秒）
     */
    @Bean
    public Request.Options requestOptions() {
        return new Request.Options(
                5, TimeUnit.SECONDS,   // 连接超时
                30, TimeUnit.SECONDS,  // 读取超时（覆盖AI决策场景）
                true                   // 允许跟随重定向
        );
    }

    /**
     * 重试策略：最多3次，100ms起（指数退避，最大1s）
     *
     * <p>注意：仅对IOException（网络异常）重试，HTTP 4xx/5xx不重试
     */
    @Bean
    public Retryer feignRetryer() {
        return new Retryer.Default(100, 1000, 3);
    }

    /**
     * Feign日志级别
     * NONE    - 无日志
     * BASIC   - 请求方法/URL/响应状态
     * HEADERS - BASIC + 请求响应头
     * FULL    - HEADERS + 请求响应体（dev环境使用）
     */
    @Bean
    public Logger.Level feignLoggerLevel() {
        return Logger.Level.BASIC;
    }

    /**
     * 请求拦截器：自动传递用户信息/TraceId/内部服务标记
     */
    @Bean
    public FeignRequestInterceptor feignRequestInterceptor() {
        return new FeignRequestInterceptor();
    }

    /**
     * 错误解码器：将下游错误响应转换为BizException
     */
    @Bean
    public ErrorDecoder feignErrorDecoder() {
        return new FeignErrorDecoder();
    }
}
