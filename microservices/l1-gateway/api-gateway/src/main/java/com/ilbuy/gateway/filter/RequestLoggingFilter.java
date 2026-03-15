package com.ilbuy.gateway.filter;

import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.UUID;

/**
 * 请求审计日志全局过滤器
 *
 * <p>记录每个请求的：traceId / userId / method / path / clientIp / 耗时 / 响应状态
 * 同时注入 X-Trace-Id 请求头，实现全链路追踪。
 *
 * @author ILbuy Team
 */
@Slf4j
@Component
public class RequestLoggingFilter implements GlobalFilter, Ordered {

    private static final int ORDER = -300;   // 最先执行，记录完整耗时
    private static final String HEADER_TRACE_ID = "X-Trace-Id";

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        long startTime = System.currentTimeMillis();
        String traceId = UUID.randomUUID().toString().replace("-", "");

        ServerHttpRequest mutatedRequest = exchange.getRequest().mutate()
            .header(HEADER_TRACE_ID, traceId)
            .build();

        ServerWebExchange mutatedExchange = exchange.mutate().request(mutatedRequest).build();

        String method = exchange.getRequest().getMethod().name();
        String path = exchange.getRequest().getURI().getPath();
        String userId = exchange.getRequest().getHeaders().getFirst("X-User-Id");
        String clientIp = getClientIp(exchange);

        log.info("[GW-IN ] traceId={} userId={} ip={} {} {}", traceId, userId, clientIp, method, path);

        return chain.filter(mutatedExchange)
            .doFinally(signal -> {
                long elapsed = System.currentTimeMillis() - startTime;
                int status = mutatedExchange.getResponse().getStatusCode() != null
                    ? mutatedExchange.getResponse().getStatusCode().value()
                    : 0;
                log.info("[GW-OUT] traceId={} status={} elapsed={}ms {} {}",
                    traceId, status, elapsed, method, path);
            });
    }

    private String getClientIp(ServerWebExchange exchange) {
        String xff = exchange.getRequest().getHeaders().getFirst("X-Forwarded-For");
        if (xff != null && !xff.isEmpty()) {
            return xff.split(",")[0].trim();
        }
        return exchange.getRequest().getRemoteAddress() != null
            ? exchange.getRequest().getRemoteAddress().getAddress().getHostAddress()
            : "unknown";
    }

    @Override
    public int getOrder() {
        return ORDER;
    }
}
