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
 * JWT 认证过滤器（每次请求执行一次）
 *
 * <p><b>处理流程：</b>
 * <ol>
 *   <li>白名单路径 → 直接放行</li>
 *   <li>内部服务调用（携带 X-Inner-Call 密钥）→ 从 Header 取用户信息，跳过 JWT 校验</li>
 *   <li>提取 Authorization Header 中的 Bearer Token</li>
 *   <li>校验 Token（含黑名单检查）</li>
 *   <li>解析 Claims，构建 {@link LoginUser}，注入 SecurityContext</li>
 *   <li>透传用户信息 Header（X-User-Id / X-User-Type）供下游服务使用</li>
 *   <li>Token 即将过期时，响应头添加 X-Token-About-Expire: true 提示客户端刷新</li>
 * </ol>
 *
 * @author ILbuy Team
 * @version 1.1.0
 */
@Slf4j
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtTokenProvider jwtTokenProvider;
    private final JwtProperties    jwtProperties;

    /** 无需鉴权的白名单路径（AntPath 匹配）*/
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
            "/doc.html",
            "/favicon.ico"
    );

    private static final AntPathMatcher PATH_MATCHER = new AntPathMatcher();

    @Override
    protected void doFilterInternal(
            HttpServletRequest  request,
            HttpServletResponse response,
            FilterChain         filterChain) throws ServletException, IOException {

        String uri = request.getRequestURI();

        // ── Step 1: 白名单直接放行 ─────────────────────────────
        if (isWhitelisted(uri)) {
            filterChain.doFilter(request, response);
            return;
        }

        // ── Step 2: 内部服务调用（跳过 JWT，从 Header 取用户信息）──
        if (isInnerServiceCall(request)) {
            String userId   = request.getHeader(CommonConstants.HEADER_USER_ID);
            String userType = request.getHeader(CommonConstants.HEADER_USER_TYPE);
            if (userId != null) {
                setSecurityContext(userId, userType != null ? userType : "B2C",
                        "FREE", "WEB", null, request);
            }
            filterChain.doFilter(request, response);
            return;
        }

        // ── Step 3: 提取 Token ────────────────────────────────
        String bearerToken = request.getHeader(jwtProperties.getTokenHeader());
        String token = jwtTokenProvider.resolveToken(bearerToken);

        if (token == null) {
            // 无 Token，不设置认证信息（由 Spring Security 路由规则决定是否允许匿名访问）
            filterChain.doFilter(request, response);
            return;
        }

        // ── Step 4: 校验 Token ────────────────────────────────
        try {
            if (!jwtTokenProvider.validateToken(token)) {
                // validateToken 内部已区分 expired / invalid，
                // 此处统一返回 TOKEN_INVALID（让客户端重新登录）
                writeErrorResponse(response, ResultCode.TOKEN_INVALID);
                return;
            }

            // ── Step 5: 解析 Claims，注入 SecurityContext ──────
            Claims claims      = jwtTokenProvider.parseToken(token);
            String userId      = claims.getSubject();
            String userType    = (String) claims.get("userType");
            String memberLevel = (String) claims.get("memberLevel");
            String clientType  = (String) claims.get("clientType");

            setSecurityContext(userId, userType, memberLevel, clientType, token, request);

            // ── Step 6: 透传用户信息到响应头（供网关/下游服务使用）──
            response.setHeader(CommonConstants.HEADER_USER_ID,   userId);
            response.setHeader(CommonConstants.HEADER_USER_TYPE, userType != null ? userType : "B2C");

            // ── Step 7: Token 即将过期提示 ────────────────────
            if (jwtTokenProvider.isTokenAboutToExpire(token)) {
                response.setHeader("X-Token-About-Expire", "true");
            }

            filterChain.doFilter(request, response);

        } catch (BizException e) {
            // ✅ 修复：直接使用 BizException 携带的 code 判断，
            //    不再错误调用 ResultCode.valueOf(String message)
            ResultCode resultCode = e.getCode() == ResultCode.TOKEN_EXPIRED.getCode()
                    ? ResultCode.TOKEN_EXPIRED
                    : ResultCode.TOKEN_INVALID;
            log.warn("[JwtFilter] Token 校验失败: URI={}, code={}, msg={}",
                    uri, e.getCode(), e.getMessage());
            writeErrorResponse(response, resultCode);
        }
    }

    // ==================== 私有方法 ====================

    /**
     * 将用户信息注入 Spring Security 上下文
     */
    private void setSecurityContext(
            String userId, String userType, String memberLevel,
            String clientType, String token, HttpServletRequest request) {
        try {
            LoginUser loginUser = LoginUser.builder()
                    .userId(Long.parseLong(userId))
                    .userType(userType    != null ? userType    : "B2C")
                    .memberLevel(memberLevel != null ? memberLevel : "FREE")
                    .enabled(true)
                    .currentToken(token)
                    .build();

            UsernamePasswordAuthenticationToken authentication =
                    new UsernamePasswordAuthenticationToken(
                            loginUser, null, loginUser.getAuthorities());
            authentication.setDetails(
                    new WebAuthenticationDetailsSource().buildDetails(request));
            SecurityContextHolder.getContext().setAuthentication(authentication);

        } catch (NumberFormatException e) {
            log.warn("[JwtFilter] userId 格式非法: {}", userId);
        }
    }

    /**
     * 写入 JSON 格式的错误响应
     */
    private void writeErrorResponse(HttpServletResponse response, ResultCode resultCode)
            throws IOException {
        response.setStatus(HttpStatus.UNAUTHORIZED.value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        response.getWriter().write(JsonUtils.toJson(Result.fail(resultCode)));
    }

    /**
     * 判断是否为白名单路径
     */
    private boolean isWhitelisted(String uri) {
        return WHITE_LIST.stream().anyMatch(p -> PATH_MATCHER.match(p, uri));
    }

    /**
     * 判断是否为内部服务调用
     * 校验 X-Inner-Call Header 是否携带正确密钥
     */
    private boolean isInnerServiceCall(HttpServletRequest request) {
        return CommonConstants.INNER_CALL_SECRET.equals(
                request.getHeader(CommonConstants.HEADER_INNER_CALL));
    }
}
