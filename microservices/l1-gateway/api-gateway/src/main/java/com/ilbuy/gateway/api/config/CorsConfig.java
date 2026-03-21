package com.ilbuy.gateway.api.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.reactive.CorsConfigurationSource;
import org.springframework.web.cors.reactive.CorsWebFilter;
import org.springframework.web.cors.reactive.UrlBasedCorsConfigurationSource;

import java.time.Duration;
import java.util.List;

/**
 * 跨域（CORS）配置
 *
 * <p>网关集中处理跨域，下游微服务无需再配置 CORS。</p>
 *
 * <p>安全策略：
 * <ul>
 *   <li>生产环境应将 allowedOriginPatterns 限定为实际前端域名</li>
 *   <li>开发/测试环境允许 * 方便调试</li>
 * </ul>
 * </p>
 */
@Configuration
public class CorsConfig {

    @Bean
    public CorsWebFilter corsWebFilter() {
        return new CorsWebFilter(corsConfigurationSource());
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration config = new CorsConfiguration();

        // 允许的来源（生产改为 https://www.ilbuy.com 等实际域名）
        config.setAllowedOriginPatterns(List.of("*"));

        // 允许的 HTTP 方法
        config.setAllowedMethods(List.of(
                HttpMethod.GET.name(),
                HttpMethod.POST.name(),
                HttpMethod.PUT.name(),
                HttpMethod.PATCH.name(),
                HttpMethod.DELETE.name(),
                HttpMethod.OPTIONS.name()
        ));

        // 允许的请求头
        config.setAllowedHeaders(List.of(
                HttpHeaders.AUTHORIZATION,
                HttpHeaders.CONTENT_TYPE,
                HttpHeaders.ACCEPT,
                "X-Trace-Id",
                "X-Tenant-Id",
                "X-Requested-With"
        ));

        // 允许携带 Cookie（跨域 Session 场景）
        config.setAllowCredentials(true);

        // 预检请求缓存 30 分钟
        config.setMaxAge(Duration.ofMinutes(30).getSeconds());

        // 暴露给前端读取的响应头
        config.setExposedHeaders(List.of(
                HttpHeaders.CONTENT_DISPOSITION,
                "X-Trace-Id"
        ));

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return source;
    }
}
