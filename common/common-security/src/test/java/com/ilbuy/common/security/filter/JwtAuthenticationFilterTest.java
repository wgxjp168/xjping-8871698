package com.ilbuy.common.security.filter;

import com.ilbuy.common.security.jwt.JwtTokenProvider;
import com.ilbuy.common.security.model.LoginUser;
import jakarta.servlet.FilterChain;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.core.context.SecurityContextHolder;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

@DisplayName("JwtAuthenticationFilter 单元测试")
@ExtendWith(MockitoExtension.class)
class JwtAuthenticationFilterTest {

    @Mock JwtTokenProvider jwtTokenProvider;
    @Mock HttpServletRequest  request;
    @Mock HttpServletResponse response;
    @Mock FilterChain filterChain;

    private JwtAuthenticationFilter filter;

    @BeforeEach
    void setUp() {
        filter = new JwtAuthenticationFilter(jwtTokenProvider);
        SecurityContextHolder.clearContext();
    }

    @Test
    @DisplayName("有效 Bearer Token → SecurityContext 写入 Authentication")
    void validToken_setsAuthentication() throws Exception {
        LoginUser user = LoginUser.builder()
                .userId(42L).username("li4").roles(List.of("ROLE_USER")).build();

        when(request.getHeader("Authorization")).thenReturn("Bearer valid.jwt.token");
        when(request.getParameter("token")).thenReturn(null);
        when(request.getServletPath()).thenReturn("/api/product/list");
        when(jwtTokenProvider.validateToken("valid.jwt.token")).thenReturn(true);
        when(jwtTokenProvider.parseToLoginUser("valid.jwt.token")).thenReturn(user);

        filter.doFilterInternal(request, response, filterChain);

        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNotNull();
        assertThat(SecurityContextHolder.getContext().getAuthentication().getName())
                .isEqualTo("li4");
        verify(filterChain, times(1)).doFilter(request, response);
    }

    @Test
    @DisplayName("无 Token → SecurityContext 为空，仍放行")
    void noToken_emptyContext_chainContinues() throws Exception {
        when(request.getHeader("Authorization")).thenReturn(null);
        when(request.getParameter("token")).thenReturn(null);
        when(request.getServletPath()).thenReturn("/api/product/list");

        filter.doFilterInternal(request, response, filterChain);

        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
        verify(filterChain, times(1)).doFilter(request, response);
    }

    @Test
    @DisplayName("Token 校验失败 → SecurityContext 为空，仍放行")
    void invalidToken_emptyContext_chainContinues() throws Exception {
        when(request.getHeader("Authorization")).thenReturn("Bearer bad.token");
        when(request.getParameter("token")).thenReturn(null);
        when(request.getServletPath()).thenReturn("/api/order/create");
        when(jwtTokenProvider.validateToken("bad.token")).thenReturn(false);

        filter.doFilterInternal(request, response, filterChain);

        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
        verify(filterChain, times(1)).doFilter(request, response);
    }

    @Test
    @DisplayName("Query Param token 也能识别")
    void queryParamToken_recognized() throws Exception {
        LoginUser user = LoginUser.builder()
                .userId(99L).username("wang5").roles(List.of()).build();

        when(request.getHeader("Authorization")).thenReturn(null);
        when(request.getParameter("token")).thenReturn("query.token.here");
        when(request.getServletPath()).thenReturn("/api/export/download");
        when(jwtTokenProvider.validateToken("query.token.here")).thenReturn(true);
        when(jwtTokenProvider.parseToLoginUser("query.token.here")).thenReturn(user);

        filter.doFilterInternal(request, response, filterChain);

        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNotNull();
    }

    @Test
    @DisplayName("Actuator 健康检查路径跳过过滤")
    void actuatorHealth_skipped() throws Exception {
        when(request.getServletPath()).thenReturn("/actuator/health");
        boolean skip = filter.shouldNotFilter(request);
        assertThat(skip).isTrue();
    }
}
