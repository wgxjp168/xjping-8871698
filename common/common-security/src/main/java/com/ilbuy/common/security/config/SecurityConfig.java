package com.ilbuy.common.security.config;

import com.ilbuy.common.security.filter.JwtAuthenticationFilter;
import com.ilbuy.common.security.handler.SecurityExceptionHandler;
import com.ilbuy.common.security.jwt.JwtTokenProvider;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * Spring Security 核心配置
 *
 * <p>设计原则：
 * <ul>
 *   <li>无状态（JWT，禁用 Session）</li>
 *   <li>CSRF 禁用（前后端分离）</li>
 *   <li>方法级别权限控制（@PreAuthorize）</li>
 *   <li>统一异常响应（JSON）</li>
 * </ul>
 * </p>
 *
 * <p>各微服务继承此配置，再通过 {@code @Bean} 重写 {@code SecurityFilterChain}
 * 来定制各自的 permitAll 路径。</p>
 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity(prePostEnabled = true, securedEnabled = true)
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtTokenProvider jwtTokenProvider;
    private final SecurityExceptionHandler securityExceptionHandler;

    /**
     * 默认 permitAll 路径（各微服务可通过 SecurityWhitelistProperties 扩展）
     */
    private static final String[] DEFAULT_WHITELIST = {
            "/actuator/health",
            "/actuator/info",
            "/v3/api-docs/**",
            "/swagger-ui/**",
            "/swagger-ui.html",
            "/error"
    };

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            // 禁用 CSRF（前后端分离，使用 JWT）
            .csrf(AbstractHttpConfigurer::disable)

            // 禁用 HTTP Basic
            .httpBasic(AbstractHttpConfigurer::disable)

            // 无状态 Session（JWT）
            .sessionManagement(session ->
                    session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))

            // 请求授权规则
            .authorizeHttpRequests(auth -> auth
                    .requestMatchers(DEFAULT_WHITELIST).permitAll()
                    .anyRequest().authenticated())

            // 异常处理
            .exceptionHandling(exception -> exception
                    .authenticationEntryPoint(securityExceptionHandler)
                    .accessDeniedHandler(securityExceptionHandler))

            // 在 UsernamePasswordAuthenticationFilter 前插入 JWT 过滤器
            .addFilterBefore(jwtAuthenticationFilter(), UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }

    @Bean
    public JwtAuthenticationFilter jwtAuthenticationFilter() {
        return new JwtAuthenticationFilter(jwtTokenProvider);
    }

    /**
     * BCrypt 密码编码器（强度 12）
     */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(12);
    }

    /**
     * AuthenticationManager（供登录服务注入使用）
     */
    @Bean
    public AuthenticationManager authenticationManager(
            AuthenticationConfiguration authConfig) throws Exception {
        return authConfig.getAuthenticationManager();
    }
}
