package com.ilbuy.common.security.config;

import com.ilbuy.common.security.filter.JwtAuthenticationFilter;
import com.ilbuy.common.security.handler.AccessDeniedHandlerImpl;
import com.ilbuy.common.security.handler.AuthenticationEntryPointImpl;
import com.ilbuy.common.security.jwt.JwtProperties;
import com.ilbuy.common.security.jwt.JwtTokenProvider;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
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
 * Spring Security 自动配置类
 *
 * <p>配置说明：
 * <ul>
 *   <li>无状态JWT认证，关闭Session</li>
 *   <li>关闭CSRF（前后端分离）</li>
 *   <li>白名单路径无需认证</li>
 *   <li>支持方法级权限控制 @PreAuthorize</li>
 *   <li>B2B/B2C角色隔离</li>
 * </ul>
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@AutoConfiguration
@EnableWebSecurity
@EnableMethodSecurity(prePostEnabled = true)
@EnableConfigurationProperties(JwtProperties.class)
@RequiredArgsConstructor
public class SecurityAutoConfiguration {

    private final AuthenticationEntryPointImpl authenticationEntryPoint;
    private final AccessDeniedHandlerImpl accessDeniedHandler;
    private final JwtTokenProvider jwtTokenProvider;
    private final JwtProperties jwtProperties;

    /**
     * Security过滤链配置
     */
    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            // 关闭CSRF（前后端分离，不需要）
            .csrf(AbstractHttpConfigurer::disable)

            // 关闭默认表单登录
            .formLogin(AbstractHttpConfigurer::disable)

            // 无状态Session（JWT模式）
            .sessionManagement(session ->
                    session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))

            // 路径权限配置
            .authorizeHttpRequests(auth -> auth
                    // 白名单：注册/登录/验证码/健康检查/API文档
                    .requestMatchers(
                            "/api/v1/users/register",
                            "/api/v1/users/login",
                            "/api/v1/users/token/refresh",
                            "/api/v1/users/captcha/**",
                            "/actuator/health",
                            "/actuator/info",
                            "/actuator/prometheus",
                            "/v3/api-docs/**",
                            "/swagger-ui/**",
                            "/swagger-ui.html",
                            "/doc.html"
                    ).permitAll()

                    // B2B专属接口（企业采购）
                    .requestMatchers("/api/v1/b2b/**").hasRole("B2B")

                    // 其他接口需认证
                    .anyRequest().authenticated()
            )

            // 自定义异常处理
            .exceptionHandling(exception -> exception
                    .authenticationEntryPoint(authenticationEntryPoint)
                    .accessDeniedHandler(accessDeniedHandler))

            // 在UsernamePassword过滤器之前插入JWT过滤器
            .addFilterBefore(
                    new JwtAuthenticationFilter(jwtTokenProvider, jwtProperties),
                    UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }

    /**
     * 密码加密器（BCrypt，12轮）
     */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(12);
    }
}
