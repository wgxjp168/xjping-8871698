package com.ilbuy.common.security.filter;

import com.ilbuy.common.core.constants.CommonConstants;
import com.ilbuy.common.security.jwt.JwtTokenProvider;
import com.ilbuy.common.security.model.LoginUser;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * JWT 认证过滤器
 * <p>每个请求只执行一次（继承 OncePerRequestFilter）。</p>
 *
 * <p>处理流程：
 * <ol>
 *   <li>从 Authorization 请求头提取 Bearer Token</li>
 *   <li>校验 Token 有效性（含黑名单）</li>
 *   <li>解析用户信息，写入 SecurityContext</li>
 *   <li>传播请求头（userId/username/roles）供下游微服务使用</li>
 * </ol>
 * </p>
 */
@Slf4j
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtTokenProvider jwtTokenProvider;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {

        String token = resolveToken(request);

        if (StringUtils.hasText(token) && jwtTokenProvider.validateToken(token)) {
            try {
                LoginUser loginUser = jwtTokenProvider.parseToLoginUser(token);

                UsernamePasswordAuthenticationToken authentication =
                        new UsernamePasswordAuthenticationToken(
                                loginUser, null, loginUser.getAuthorities());
                authentication.setDetails(
                        new WebAuthenticationDetailsSource().buildDetails(request));

                SecurityContextHolder.getContext().setAuthentication(authentication);

                log.debug("[JWT Filter] 认证成功 userId={} username={}",
                        loginUser.getUserId(), loginUser.getUsername());

            } catch (Exception e) {
                log.warn("[JWT Filter] 解析 Token 失败: {}", e.getMessage());
                SecurityContextHolder.clearContext();
            }
        }

        filterChain.doFilter(request, response);
    }

    /**
     * 优先从 Authorization 头取 Token，其次从查询参数 token 取
     */
    private String resolveToken(HttpServletRequest request) {
        // 1. Header: Authorization: Bearer <token>
        String authHeader = request.getHeader(CommonConstants.HEADER_AUTHORIZATION);
        String token = JwtTokenProvider.extractFromHeader(authHeader);
        if (StringUtils.hasText(token)) {
            return token;
        }
        // 2. 查询参数（适用于 WebSocket/下载接口）
        String queryToken = request.getParameter("token");
        if (StringUtils.hasText(queryToken)) {
            return queryToken;
        }
        return null;
    }

    /**
     * 跳过不需要认证的路径（在 SecurityConfig 中已配置 permitAll，此处可额外快速跳过）
     */
    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getServletPath();
        return path.startsWith("/actuator/health")
                || path.startsWith("/actuator/info");
    }
}
