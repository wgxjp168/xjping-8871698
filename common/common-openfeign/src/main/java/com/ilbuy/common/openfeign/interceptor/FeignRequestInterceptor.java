package com.ilbuy.common.openfeign.interceptor;

import com.ilbuy.common.core.constant.CommonConstants;
import com.ilbuy.common.security.context.LoginUser;
import com.ilbuy.common.security.context.SecurityUtils;
import feign.RequestInterceptor;
import feign.RequestTemplate;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.util.UUID;

/**
 * Feign 请求拦截器
 *
 * <p>在微服务间Feign调用时，自动传递以下请求头：
 * <ul>
 *   <li>Authorization - JWT Token（透传，下游服务可复用）</li>
 *   <li>X-User-Id - 当前用户ID</li>
 *   <li>X-User-Type - 用户类型（B2B/B2C）</li>
 *   <li>X-Trace-Id - 链路追踪ID（不存在则生成）</li>
 *   <li>X-Inner-Call - 内部服务标记（下游跳过JWT校验）</li>
 * </ul>
 *
 * <p>注意：内部服务调用传递 X-Inner-Call Secret，
 * 下游 JwtAuthenticationFilter 校验此头后跳过JWT校验，
 * 直接从 X-User-Id 头中提取用户信息。
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@Slf4j
public class FeignRequestInterceptor implements RequestInterceptor {

    @Override
    public void apply(RequestTemplate template) {
        // 标记为内部服务调用（下游跳过JWT校验）
        template.header(CommonConstants.HEADER_INNER_CALL, CommonConstants.INNER_CALL_SECRET);

        // 传递链路追踪ID
        String traceId = getTraceIdFromRequest();
        if (traceId == null) {
            traceId = UUID.randomUUID().toString().replace("-", "");
        }
        template.header(CommonConstants.HEADER_TRACE_ID, traceId);

        // 从当前请求获取并传递用户信息
        try {
            LoginUser currentUser = SecurityUtils.currentUserOrNull();
            if (currentUser != null) {
                template.header(CommonConstants.HEADER_USER_ID,
                        String.valueOf(currentUser.getUserId()));
                template.header(CommonConstants.HEADER_USER_TYPE,
                        currentUser.getUserType());
            }
        } catch (Exception e) {
            log.debug("[FeignInterceptor] 无法获取当前用户信息（非HTTP上下文）");
        }

        // 透传原始Authorization Token（可选，下游服务可能需要）
        String authHeader = getAuthHeaderFromRequest();
        if (authHeader != null) {
            template.header(CommonConstants.HEADER_AUTHORIZATION, authHeader);
        }

        log.debug("[FeignInterceptor] 请求头注入完成: target={} {}",
                template.method(), template.url());
    }

    /**
     * 从当前HTTP请求中获取TraceId
     */
    private String getTraceIdFromRequest() {
        try {
            ServletRequestAttributes attrs =
                    (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attrs != null) {
                HttpServletRequest request = attrs.getRequest();
                return request.getHeader(CommonConstants.HEADER_TRACE_ID);
            }
        } catch (Exception e) {
            log.debug("[FeignInterceptor] 无法获取TraceId");
        }
        return null;
    }

    /**
     * 从当前HTTP请求中获取Authorization Token
     */
    private String getAuthHeaderFromRequest() {
        try {
            ServletRequestAttributes attrs =
                    (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attrs != null) {
                return attrs.getRequest().getHeader(CommonConstants.HEADER_AUTHORIZATION);
            }
        } catch (Exception e) {
            log.debug("[FeignInterceptor] 无法获取Authorization Header");
        }
        return null;
    }
}
