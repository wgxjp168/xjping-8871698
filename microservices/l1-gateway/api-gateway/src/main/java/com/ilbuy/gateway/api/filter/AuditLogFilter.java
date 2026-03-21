package com.ilbuy.gateway.api.filter;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 请求审计日志过滤器（Order = -50）
 *
 * <p>记录每个请求的：TraceID / UID / 路径 / 方法 / 耗时 / 状态码。</p>
 *
 * <p>日志格式（JSON structured logging，方便 ELK 解析）：</p>
 * <pre>
 * {
 *   "type":       "GATEWAY_AUDIT",
 *   "traceId":    "a1b2c3d4e5f6...",
 *   "userId":     "10001",
 *   "method":     "POST",
 *   "path":       "/api/v1/dialog/chat",
 *   "clientIp":   "1.2.3.4",
 *   "statusCode": 200,
 *   "durationMs": 32,
 *   "timestamp":  1720000000000
 * }
 * </pre>
 *
 * <p>推送至 ELK：配置 Logstash appender 消费 {@code GATEWAY_AUDIT} 类型日志。</p>
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AuditLogFilter implements GlobalFilter, Ordered {

    private static final int ORDER = -50;
    private static final String HEADER_USER_ID   = "X-User-Id";
    private static final String HEADER_CLIENT_IP = "X-Forwarded-For";

    private final ObjectMapper objectMapper;

    @Override
    public int getOrder() {
        return ORDER;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        long startMs = Instant.now().toEpochMilli();
        ServerHttpRequest request = exchange.getRequest();

        return chain.filter(exchange)
                .doFinally(signal -> {
                    long durationMs = Instant.now().toEpochMilli() - startMs;

                    int statusCode = exchange.getResponse().getStatusCode() != null
                            ? exchange.getResponse().getStatusCode().value()
                            : 0;

                    String traceId = exchange.getResponse().getHeaders()
                            .getFirst(TraceIdGlobalFilter.TRACE_ID_HEADER);
                    String userId  = request.getHeaders().getFirst(HEADER_USER_ID);
                    String clientIp = resolveClientIp(request);

                    // 构建结构化审计日志（ELK 解析）
                    Map<String, Object> auditLog = new LinkedHashMap<>();
                    auditLog.put("type",       "GATEWAY_AUDIT");
                    auditLog.put("traceId",    traceId);
                    auditLog.put("userId",     userId);
                    auditLog.put("method",     request.getMethod().name());
                    auditLog.put("path",       request.getPath().value());
                    auditLog.put("query",      request.getURI().getQuery());
                    auditLog.put("clientIp",   clientIp);
                    auditLog.put("statusCode", statusCode);
                    auditLog.put("durationMs", durationMs);
                    auditLog.put("timestamp",  startMs);

                    try {
                        // 使用 info 级别输出 JSON，Logstash 配置 JSON 解析器可直接入库
                        log.info(objectMapper.writeValueAsString(auditLog));
                    } catch (Exception e) {
                        log.warn("[Audit] 序列化失败 traceId={} path={} err={}",
                                traceId, request.getPath().value(), e.getMessage());
                    }
                });
    }

    private String resolveClientIp(ServerHttpRequest request) {
        String xff = request.getHeaders().getFirst(HEADER_CLIENT_IP);
        if (xff != null && !xff.isBlank()) {
            return xff.split(",")[0].trim();
        }
        if (request.getRemoteAddress() != null) {
            return request.getRemoteAddress().getAddress().getHostAddress();
        }
        return "unknown";
    }
}
