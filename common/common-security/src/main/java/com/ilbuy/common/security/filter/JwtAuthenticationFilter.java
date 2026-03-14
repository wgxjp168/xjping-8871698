package com.ilbuy.common.security.filter;

import com.ilbuy.common.core.constant.CommonConstants;
import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.common.core.result.Result;
import com.ilbuy.common.core.result.ResultCode;
import com.ilbuy.common.core.utils.JsonUtils;
import com.ilbuy.common.security.context.LoginUser;
import com.ilbuy.common.security.jwt.JwtProperties;
import com.ilbuy.common.security.jwt.JwtTokenProvider;
import io.jsonwebtoken.Claims;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * JWT认证过滤器
 *
 * <p>每次请求执行一次，流程：
 * <ol>
 *   <li>检查是否为白名单路径（跳过认证）</li>
 *   <li>检查是否为内部服务调用（跳过JWT校验）</li>
 *   <li>提取 Authorization Header 中的 Token</li>
 *   <li>解析 Token，验证合法性</li>
 *   <li>将用户信息注入 SecurityContext</li>
 *   <li>在响应头中传递用户ID（供下游服务使用）</li>
 * </ol>
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@Slf4j
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtTokenProvider jwtTokenProvider;
    private final JwtProperties jwtProperties;

    /** 不需要认证的白名单路径 */
    private static final List<String> WHITE_LIST = List.of(
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
    );

    private static final AntPathMatcher PATH_MATCHER = new AntPathMatcher();

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain) throws ServletException, IOException {

        String requestURI = request.getRequestURI();

        // 1. 白名单路径直接放行
        if (isWhitelisted(requestURI)) {
            filterChain.doFilter(request, response);
            return;
        }

        // 2. 内部服务调用（通过密钥验证），跳过JWT
        if (isInnerServiceCall(request)) {
            String userId = request.getHeader(CommonConstants.HEADER_USER_ID);
            String userType = request.getHeader(CommonConstants.HEADER_USER_TYPE);
            if (userId != null) {
                setSecurityContext(userId, userType != null ? userType : "B2C", "FREE", null, request);
            }
            filterChain.doFilter(request, response);
            return;
        }

        // 3. 提取 Token
        String bearerToken = request.getHeader(jwtProperties.getTokenHeader());
        String token = jwtTokenProvider.resolveToken(bearerToken);

        if (token == null) {
            // 无Token，不设置认证信息（后续Security配置决定是否放行）
            filterChain.doFilter(request, response);
            return;
        }

        // 4. 解析并校验 Token
        try {
            if (!jwtTokenProvider.validateToken(token)) {
                writeErrorResponse(response, ResultCode.TOKEN_INVALID);
                return;
            }

            Claims claims = jwtTokenProvider.parseToken(token);
            String userId = claims.getSubject();
            String userType = (String) claims.get("userType");
            String memberLevel = (String) claims.get("memberLevel");

            // 5. 注入 SecurityContext
            setSecurityContext(userId, userType, memberLevel, token, request);

            // 6. 向响应头传递用户ID（供下游微服务使用）
            response.setHeader(CommonConstants.HEADER_USER_ID, userId);
            response.setHeader(CommonConstants.HEADER_USER_TYPE, userType != null ? userType : "B2C");

            // 7. Token 即将过期时，在响应头提示客户端刷新
            if (jwtTokenProvider.isTokenAboutToExpire(token)) {
                response.setHeader("X-Token-About-Expire", "true");
            }

            filterChain.doFilter(request, response);

        } catch (BizException e) {
            log.warn("[JWT Filter] 认证失败: URI={}, error={}", requestURI, e.getMessage());
            writeErrorResponse(response, ResultCode.valueOf(e.getMessage()) != null
                    ? ResultCode.TOKEN_EXPIRED : ResultCode.TOKEN_INVALID);
        }
    }

    /**
     * 设置 Spring Security 上下文
     */
    private void setSecurityContext(
            String userId, String userType, String memberLevel,
            String token, HttpServletRequest request) {

        LoginUser loginUser = LoginUser.builder()
                .userId(Long.parseLong(userId))
                .userType(userType != null ? userType : "B2C")
                .memberLevel(memberLevel != null ? memberLevel : "FREE")
                .enabled(true)
                .currentToken(token)
                .build();

        UsernamePasswordAuthenticationToken authentication =
                new UsernamePasswordAuthenticationToken(loginUser, null, loginUser.getAuthorities());
        authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
        SecurityContextHolder.getContext().setAuthentication(authentication);
    }

    /**
     * 写入错误响应（JSON格式）
     */
    private void writeErrorResponse(HttpServletResponse response, ResultCode resultCode) throws IOException {
        response.setStatus(HttpStatus.UNAUTHORIZED.value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        String body = JsonUtils.toJson(Result.fail(resultCode));
        response.getWriter().write(body);
    }

    /**
     * 判断是否为白名单路径
     */
    private boolean isWhitelisted(String uri) {
        return WHITE_LIST.stream().anyMatch(pattern -> PATH_MATCHER.match(pattern, uri));
    }

    /**
     * 判断是否为内部服务调用（通过X-Inner-Call头）
     */
    private boolean isInnerServiceCall(HttpServletRequest request) {
        String innerSecret = request.getHeader(CommonConstants.HEADER_INNER_CALL);
        return CommonConstants.INNER_CALL_SECRET.equals(innerSecret);
    }
}
