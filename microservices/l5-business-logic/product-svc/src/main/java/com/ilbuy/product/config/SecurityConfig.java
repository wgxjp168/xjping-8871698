package com.ilbuy.product.config;

import com.ilbuy.product.security.JwtAuthFilter;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableMethodSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtAuthFilter jwtAuthFilter;

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(AbstractHttpConfigurer::disable)
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                // Public endpoints — gateway whitelist, no auth needed
                .requestMatchers(HttpMethod.GET, "/api/v1/products/search").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/v1/products/*/detail").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/v1/products/*/platforms").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/v1/products/categories").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/v1/products/categories/**").permitAll()
                .requestMatchers("/actuator/**").permitAll()
                // All other requests require authentication
                .anyRequest().authenticated()
            )
            .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }
}
