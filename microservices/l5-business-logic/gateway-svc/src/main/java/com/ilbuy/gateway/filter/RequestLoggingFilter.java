package com.ilbuy.gateway.filter;

import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

/**
 * 全局请求/响应日志过滤器
 * 记录：method + path + 耗时 + 响应状态
 */
@Component
@Slf4j
public class RequestLoggingFilter implements GlobalFilter, Ordered {

    private static final String START_TIME_ATTR = "gateway.startTime";

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE;   // 最先记录开始时间
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        exchange.getAttributes().put(START_TIME_ATTR, System.currentTimeMillis());

        String userId = request.getHeaders().getFirst(JwtAuthGlobalFilter.HEADER_USER_ID);
        log.info("→ {} {} | userId={} | ip={}",
                request.getMethod(),
                request.getPath().value(),
                userId != null ? userId : "anon",
                getClientIp(request));

        return chain.filter(exchange).then(Mono.fromRunnable(() -> {
            ServerHttpResponse response = exchange.getResponse();
            Long start = exchange.getAttribute(START_TIME_ATTR);
            long elapsed = start != null ? System.currentTimeMillis() - start : -1;

            log.info("← {} {} | status={} | {}ms",
                    request.getMethod(),
                    request.getPath().value(),
                    response.getStatusCode() != null ? response.getStatusCode().value() : "?",
                    elapsed);
        }));
    }

    private String getClientIp(ServerHttpRequest request) {
        String xff = request.getHeaders().getFirst("X-Forwarded-For");
        if (xff != null && !xff.isBlank()) {
            return xff.split(",")[0].trim();
        }
        if (request.getRemoteAddress() != null) {
            return request.getRemoteAddress().getAddress().getHostAddress();
        }
        return "unknown";
    }
}
