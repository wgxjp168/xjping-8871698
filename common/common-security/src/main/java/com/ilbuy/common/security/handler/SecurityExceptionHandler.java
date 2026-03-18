package com.ilbuy.common.security.handler;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ilbuy.common.core.enums.ResultCode;
import com.ilbuy.common.core.result.Result;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.security.web.access.AccessDeniedHandler;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * Spring Security 异常处理（未认证 401 / 无权限 403）
 *
 * <p>返回统一的 JSON 格式，前端统一处理。</p>
 */
@Slf4j
@Component
public class SecurityExceptionHandler implements AuthenticationEntryPoint, AccessDeniedHandler {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    /**
     * 未认证处理（401）：Token 缺失/过期/无效
     */
    @Override
    public void commence(HttpServletRequest request,
                         HttpServletResponse response,
                         AuthenticationException authException) throws IOException {
        log.warn("[Security] 未认证访问 uri={} msg={}", request.getRequestURI(), authException.getMessage());
        writeJson(response, HttpServletResponse.SC_UNAUTHORIZED,
                Result.fail(ResultCode.UNAUTHORIZED));
    }

    /**
     * 无权限处理（403）：已认证但权限不足
     */
    @Override
    public void handle(HttpServletRequest request,
                       HttpServletResponse response,
                       AccessDeniedException accessDeniedException) throws IOException {
        log.warn("[Security] 无权限访问 uri={} user={}",
                request.getRequestURI(), request.getRemoteUser());
        writeJson(response, HttpServletResponse.SC_FORBIDDEN,
                Result.fail(ResultCode.FORBIDDEN));
    }

    private void writeJson(HttpServletResponse response, int status, Result<?> result) throws IOException {
        response.setStatus(status);
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        response.getWriter().write(MAPPER.writeValueAsString(result));
    }
}
