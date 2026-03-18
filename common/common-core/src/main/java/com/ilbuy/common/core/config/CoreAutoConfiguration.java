package com.ilbuy.common.core.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.ilbuy.common.core.aspect.NoRepeatSubmitAspect;
import com.ilbuy.common.core.aspect.RateLimitAspect;
import com.ilbuy.common.core.exception.GlobalExceptionHandler;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnWebApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.core.StringRedisTemplate;

/**
 * common-core 自动装配入口
 *
 * <p>通过 Spring Boot 3.x 的 AutoConfiguration.imports 机制自动加载，
 * 消费方无需手动 @Import 或 @ComponentScan。</p>
 *
 * <p>注册的 Bean：</p>
 * <ul>
 *   <li>{@link GlobalExceptionHandler}  — 全局异常处理（仅 Web 环境）</li>
 *   <li>{@link RateLimitAspect}         — 限流切面（需要 Redis + AOP）</li>
 *   <li>{@link NoRepeatSubmitAspect}    — 防重复提交切面（需要 Redis + AOP）</li>
 *   <li>{@link ObjectMapper}            — Jackson 全局实例（已注册 Java 8 Time 模块）</li>
 * </ul>
 */
@Configuration
public class CoreAutoConfiguration {

    // ──────────────────── Web 相关 Bean ────────────────────

    @Bean
    @ConditionalOnWebApplication
    @ConditionalOnMissingBean(GlobalExceptionHandler.class)
    public GlobalExceptionHandler globalExceptionHandler() {
        return new GlobalExceptionHandler();
    }

    // ──────────────────── AOP 切面（需要 Redis） ────────────────────

    @Bean
    @ConditionalOnClass(name = "org.springframework.data.redis.core.StringRedisTemplate")
    @ConditionalOnMissingBean(RateLimitAspect.class)
    public RateLimitAspect rateLimitAspect(StringRedisTemplate redisTemplate) {
        return new RateLimitAspect(redisTemplate);
    }

    @Bean
    @ConditionalOnClass(name = "org.springframework.data.redis.core.StringRedisTemplate")
    @ConditionalOnMissingBean(NoRepeatSubmitAspect.class)
    public NoRepeatSubmitAspect noRepeatSubmitAspect(StringRedisTemplate redisTemplate) {
        return new NoRepeatSubmitAspect(redisTemplate);
    }

    // ──────────────────── Jackson ────────────────────

    @Bean
    @ConditionalOnMissingBean(ObjectMapper.class)
    public ObjectMapper objectMapper() {
        ObjectMapper om = new ObjectMapper();
        om.registerModule(new JavaTimeModule());
        om.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        return om;
    }
}
