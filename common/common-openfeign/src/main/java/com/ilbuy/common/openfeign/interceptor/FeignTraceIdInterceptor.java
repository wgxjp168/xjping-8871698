package com.ilbuy.common.openfeign.interceptor;

import com.ilbuy.common.core.constants.CommonConstants;
import feign.RequestInterceptor;
import feign.RequestTemplate;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.MDC;
import org.springframework.util.StringUtils;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.util.UUID;

/**
 * Feign 链路追踪 ID 拦截器
 *
 * <p>职责：确保每个跨服务调用都携带唯一的 traceId，实现全链路追踪。</p>
 *
 * <p>传播策略（优先级从高到低）：</p>
 * <ol>
 *   <li>从当前 HTTP 请求头取 X-Trace-Id（已由上游设置）</li>
 *   <li>从 MDC（Logback/Log4j2 线程上下文）取 traceId</li>
 *   <li>生成新的 UUID 作为 traceId（调用链起点）</li>
 * </ol>
 *
 * <p>与 Sleuth/Micrometer Tracing 的关系：</p>
 * <ul>
 *   <li>使用 Spring Cloud Sleuth 时，Sleuth 会自动注入 traceId，此拦截器作为补充</li>
 *   <li>不使用 Sleuth 时，此拦截器独立完成 traceId 传播</li>
 * </ul>
 *
 * <pre>{@code
 * // 注册方式：在 FeignConfig 中声明 Bean
 * @Bean
 * public FeignTraceIdInterceptor feignTraceIdInterceptor() {
 *     return new FeignTraceIdInterceptor();
 * }
 * }</pre>
 */
@Slf4j
public class FeignTraceIdInterceptor implements RequestInterceptor {

    /** MDC 中 traceId 的 Key（与 Logback pattern 中 %X{traceId} 对应） */
    public static final String MDC_TRACE_ID_KEY = "traceId";

    @Override
    public void apply(RequestTemplate template) {
        String traceId = resolveTraceId();

        // 写入请求头，传递给下游
        template.removeHeader(CommonConstants.HEADER_TRACE_ID);
        template.header(CommonConstants.HEADER_TRACE_ID, traceId);

        // 同步写入 MDC（确保本服务日志也带有 traceId）
        MDC.put(MDC_TRACE_ID_KEY, traceId);

        log.debug("[FeignTrace] traceId={} url={}", traceId, template.url());
    }

    /**
     * 解析 traceId（三级降级）
     */
    private String resolveTraceId() {
        // 1. 从当前 HTTP 请求头取
        try {
            ServletRequestAttributes attrs =
                    (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attrs != null) {
                String traceId = attrs.getRequest().getHeader(CommonConstants.HEADER_TRACE_ID);
                if (StringUtils.hasText(traceId)) {
                    return traceId;
                }
            }
        } catch (Exception ignored) {}

        // 2. 从 MDC 取（异步线程 / 消息消费等场景）
        String mdcTraceId = MDC.get(MDC_TRACE_ID_KEY);
        if (StringUtils.hasText(mdcTraceId)) {
            return mdcTraceId;
        }

        // 3. 生成新 UUID（调用链起点）
        return generateTraceId();
    }

    /**
     * 生成 traceId：去连字符的 UUID 小写（32位）
     */
    public static String generateTraceId() {
        return UUID.randomUUID().toString().replace("-", "");
    }
}
