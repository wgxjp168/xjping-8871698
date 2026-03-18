package com.ilbuy.common.openfeign.interceptor;

import com.ilbuy.common.core.constants.CommonConstants;
import feign.RequestInterceptor;
import feign.RequestTemplate;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.util.StringUtils;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

/**
 * Feign Token 透传拦截器
 *
 * <p>将当前请求的 JWT Token 透传到下游微服务，实现链路认证：</p>
 * <ol>
 *   <li>优先从当前 HTTP 请求头取 Authorization（Web 调用链）</li>
 *   <li>其次从 SecurityContext 取（批处理/异步场景）</li>
 *   <li>同时传播 traceId、tenantId、userId 等上下文头</li>
 * </ol>
 *
 * <p>注册方式：在 FeignConfig 中注入为 Bean 即可。</p>
 */
@Slf4j
public class FeignTokenRelayInterceptor implements RequestInterceptor {

    @Override
    public void apply(RequestTemplate template) {
        // 1. 从 HTTP 请求上下文取 Token
        ServletRequestAttributes attrs =
                (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();

        if (attrs != null) {
            HttpServletRequest request = attrs.getRequest();
            propagateHeader(template, request, CommonConstants.HEADER_AUTHORIZATION);
            propagateHeader(template, request, CommonConstants.HEADER_TRACE_ID);
            propagateHeader(template, request, CommonConstants.HEADER_TENANT_ID);
            propagateHeader(template, request, CommonConstants.HEADER_USER_ID);
            propagateHeader(template, request, CommonConstants.HEADER_USERNAME);
            return;
        }

        // 2. 异步/批处理场景：从 SecurityContext 构建 Token 头
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getCredentials() instanceof String token
                && StringUtils.hasText(token)) {
            template.header(CommonConstants.HEADER_AUTHORIZATION,
                    CommonConstants.TOKEN_PREFIX + token);
        }

        log.debug("[FeignInterceptor] 无 HTTP 上下文，Token 透传跳过");
    }

    private void propagateHeader(RequestTemplate template,
                                  HttpServletRequest request,
                                  String headerName) {
        String value = request.getHeader(headerName);
        if (StringUtils.hasText(value)) {
            // 移除已有同名头，再设置（避免重复叠加）
            template.removeHeader(headerName);
            template.header(headerName, value);
        }
    }
}
