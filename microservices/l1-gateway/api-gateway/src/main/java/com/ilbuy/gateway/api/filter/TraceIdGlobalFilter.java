package com.ilbuy.gateway.api.filter;

import lombok.extern.slf4j.Slf4j;
import org.slf4j.MDC;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.UUID;

/**
 * TraceID 注入过滤器（优先级最高，Order = -200）
 *
 * <p>处理逻辑：
 * <ol>
 *   <li>从 {@code X-Trace-Id} 请求头读取上游传入的 TraceID</li>
 *   <li>若不存在则生成新的 32 位 UUID（去连字符）</li>
 *   <li>写入下游请求头（{@code X-Trace-Id}），保证链路可追踪</li>
 *   <li>写入响应头，方便前端排查问题</li>
 *   <li>写入 MDC，配合日志框架输出到 ELK</li>
 * </ol>
 * </p>
 */
@Slf4j
@Component
public class TraceIdGlobalFilter implements GlobalFilter, Ordered {

    public static final String TRACE_ID_HEADER = "X-Trace-Id";
    public static final String MDC_TRACE_ID    = "traceId";

    /** 优先级：最先执行（TraceID 必须在所有过滤器之前就绪） */
    private static final int ORDER = -200;

    @Override
    public int getOrder() {
        return ORDER;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String traceId = resolveTraceId(exchange);

        // 写入 MDC（响应式上下文，需通过 contextWrite 传播）
        MDC.put(MDC_TRACE_ID, traceId);

        // 向下游请求头注入 TraceID
        ServerHttpRequest mutatedRequest = exchange.getRequest().mutate()
                .header(TRACE_ID_HEADER, traceId)
                .build();

        ServerWebExchange mutatedExchange = exchange.mutate()
                .request(mutatedRequest)
                .build();

        // 将 TraceID 写入响应头
        mutatedExchange.getResponse().getHeaders().set(TRACE_ID_HEADER, traceId);

        return chain.filter(mutatedExchange)
                .contextWrite(ctx -> ctx.put(MDC_TRACE_ID, traceId))
                .doFinally(signal -> MDC.remove(MDC_TRACE_ID));
    }

    private String resolveTraceId(ServerWebExchange exchange) {
        String upstream = exchange.getRequest().getHeaders().getFirst(TRACE_ID_HEADER);
        if (upstream != null && !upstream.isBlank()) {
            return upstream.trim();
        }
        return UUID.randomUUID().toString().replace("-", "");
    }
}
