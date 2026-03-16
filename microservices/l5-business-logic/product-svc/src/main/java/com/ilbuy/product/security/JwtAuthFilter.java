package com.ilbuy.product.security;

import io.jsonwebtoken.Claims;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

@Component
@RequiredArgsConstructor
public class JwtAuthFilter extends OncePerRequestFilter {

    private final JwtUtil jwtUtil;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain)
        throws ServletException, IOException {

        // Gateway injects X-User-Id after validating the JWT; fall back to direct Bearer for dev
        String xUserId = request.getHeader("X-User-Id");
        String xUserRole = request.getHeader("X-User-Role");

        if (StringUtils.hasText(xUserId)) {
            // Trust header set by gateway
            Long userId = Long.valueOf(xUserId);
            String role = StringUtils.hasText(xUserRole) ? xUserRole : "USER";
            var auth = new UsernamePasswordAuthenticationToken(
                userId, null,
                List.of(new SimpleGrantedAuthority("ROLE_" + role))
            );
            SecurityContextHolder.getContext().setAuthentication(auth);
        } else {
            // Fallback: parse Bearer token directly (useful in local dev without gateway)
            String token = resolveToken(request);
            if (StringUtils.hasText(token) && jwtUtil.validateToken(token)) {
                Claims claims = jwtUtil.parseToken(token);
                Long userId = Long.valueOf(claims.getSubject());
                String role = claims.get("role", String.class);

                var auth = new UsernamePasswordAuthenticationToken(
                    userId, null,
                    List.of(new SimpleGrantedAuthority("ROLE_" + (role != null ? role : "USER")))
                );
                SecurityContextHolder.getContext().setAuthentication(auth);
            }
        }

        chain.doFilter(request, response);
    }

    private String resolveToken(HttpServletRequest request) {
        String bearer = request.getHeader("Authorization");
        if (StringUtils.hasText(bearer) && bearer.startsWith("Bearer ")) {
            return bearer.substring(7);
        }
        return null;
    }
}
