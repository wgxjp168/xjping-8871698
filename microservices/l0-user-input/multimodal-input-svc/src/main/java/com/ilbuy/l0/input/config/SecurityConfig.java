package com.ilbuy.l0.input.config;

import com.ilbuy.common.security.filter.JwtAuthenticationFilter;
import com.ilbuy.common.security.jwt.JwtProperties;
import com.ilbuy.common.security.jwt.JwtTokenProvider;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * Spring Security 配置（多模态输入适配服务）
 *
 * <p>安全策略：
 * <ul>
 *   <li>无状态 JWT（无Session）</li>
 *   <li>健康检查/Swagger/Prometheus 白名单</li>
 *   <li>所有业务 API 需携带有效 JWT</li>
 * </ul>
 *
 * @author ILbuy Team
 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtTokenProvider jwtTokenProvider;
    private final JwtProperties    jwtProperties;

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(AbstractHttpConfigurer::disable)
            .sessionManagement(session ->
                    session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                    // 公开端点
                    .requestMatchers(
                            "/actuator/health",
                            "/actuator/info",
                            "/actuator/prometheus",
                            "/v3/api-docs/**",
                            "/swagger-ui/**",
                            "/swagger-ui.html",
                            "/doc.html",
                            "/favicon.ico"
                    ).permitAll()
                    // 所有业务接口需鉴权
                    .anyRequest().authenticated()
            )
            .addFilterBefore(
                    new JwtAuthenticationFilter(jwtTokenProvider, jwtProperties),
                    UsernamePasswordAuthenticationFilter.class
            );

        return http.build();
    }
}
