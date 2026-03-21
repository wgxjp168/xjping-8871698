package com.ilbuy.common.security.config;

import com.ilbuy.common.security.handler.SecurityExceptionHandler;
import com.ilbuy.common.security.jwt.JwtProperties;
import com.ilbuy.common.security.jwt.JwtTokenProvider;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.security.web.SecurityFilterChain;

/**
 * common-security 自动装配入口
 *
 * <p>解决库模式（jar 依赖）下 @Component 无法被消费方 ComponentScan 覆盖的问题。
 * 通过 Spring Boot 3.x AutoConfiguration.imports 机制自动加载，消费方无需
 * 手动 @Import 或 @ComponentScan。</p>
 *
 * <p>注册的 Bean：</p>
 * <ul>
 *   <li>{@link JwtProperties}           — JWT 配置属性（@ConfigurationProperties）</li>
 *   <li>{@link JwtTokenProvider}        — JWT 生成/解析/校验（需要 Redis）</li>
 *   <li>{@link SecurityExceptionHandler} — 401/403 统一 JSON 响应</li>
 * </ul>
 *
 * <p>依赖：消费方需提供 spring-boot-starter-data-redis（StringRedisTemplate）。</p>
 */
@AutoConfiguration
@ConditionalOnClass(SecurityFilterChain.class)
@EnableConfigurationProperties(JwtProperties.class)
public class SecurityAutoConfiguration {

    /**
     * JWT Token 生成/解析组件
     *
     * <p>@ConditionalOnMissingBean 保证消费方可通过自定义 Bean 覆盖默认实现。</p>
     */
    @Bean
    @ConditionalOnMissingBean(JwtTokenProvider.class)
    public JwtTokenProvider jwtTokenProvider(JwtProperties jwtProperties,
                                              StringRedisTemplate redisTemplate) {
        return new JwtTokenProvider(jwtProperties, redisTemplate);
    }

    /**
     * Security 异常处理（401 未认证 / 403 无权限）
     */
    @Bean
    @ConditionalOnMissingBean(SecurityExceptionHandler.class)
    public SecurityExceptionHandler securityExceptionHandler() {
        return new SecurityExceptionHandler();
    }
}
