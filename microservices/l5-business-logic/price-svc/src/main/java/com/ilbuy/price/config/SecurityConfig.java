package com.ilbuy.price.config;

import com.ilbuy.price.security.JwtAuthFilter;
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
                .requestMatchers("/actuator/health", "/actuator/info").permitAll()
                // Public endpoints
                .requestMatchers(HttpMethod.GET, "/api/v1/prices/*/history").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/v1/prices/*/trend").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/v1/prices/*/compare").permitAll()
                // Authenticated endpoints
                .requestMatchers(HttpMethod.POST, "/api/v1/prices/alerts").authenticated()
                .requestMatchers(HttpMethod.GET, "/api/v1/prices/alerts").authenticated()
                .requestMatchers(HttpMethod.DELETE, "/api/v1/prices/alerts/**").authenticated()
                .anyRequest().authenticated()
            )
            .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }
}
