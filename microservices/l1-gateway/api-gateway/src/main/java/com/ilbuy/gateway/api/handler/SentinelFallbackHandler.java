package com.ilbuy.gateway.api.handler;

import com.alibaba.csp.sentinel.adapter.gateway.sc.callback.BlockRequestHandler;
import com.alibaba.csp.sentinel.slots.block.authority.AuthorityException;
import com.alibaba.csp.sentinel.slots.block.degrade.DegradeException;
import com.alibaba.csp.sentinel.slots.block.flow.FlowException;
import com.alibaba.csp.sentinel.slots.block.flow.param.ParamFlowException;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.server.ServerResponse;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.Map;

/**
 * Sentinel 熔断/限流统一降级处理器
 *
 * <p>返回统一 JSON 格式，区分场景：
 * <ul>
 *   <li>{@link FlowException}       — 限流（429）</li>
 *   <li>{@link DegradeException}    — 熔断降级（503）</li>
 *   <li>{@link ParamFlowException}  — 热点参数限流（429）</li>
 *   <li>{@link AuthorityException}  — 访问控制（403）</li>
 *   <li>其他 Sentinel 异常         — 服务不可用（503）</li>
 * </ul>
 * </p>
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class SentinelFallbackHandler implements BlockRequestHandler {

    private final ObjectMapper objectMapper;

    @Override
    public Mono<ServerResponse> handleRequest(ServerWebExchange exchange, Throwable ex) {
        String path = exchange.getRequest().getPath().value();

        if (ex instanceof FlowException || ex instanceof ParamFlowException) {
            log.warn("[Sentinel] 限流触发 path={} type={}", path, ex.getClass().getSimpleName());
            return buildResponse(429, "请求过于频繁，请稍后重试", exchange);
        }
        if (ex instanceof DegradeException) {
            log.warn("[Sentinel] 熔断降级触发 path={}", path);
            return buildResponse(503, "服务暂时不可用，请稍后重试", exchange);
        }
        if (ex instanceof AuthorityException) {
            log.warn("[Sentinel] 访问控制拦截 path={}", path);
            return buildResponse(403, "无访问权限", exchange);
        }

        log.error("[Sentinel] 未知 Sentinel 异常 path={} err={}", path, ex.getMessage());
        return buildResponse(503, "服务异常，请稍后重试", exchange);
    }

    private Mono<ServerResponse> buildResponse(int code, String message,
                                                ServerWebExchange exchange) {
        String traceId = exchange.getResponse().getHeaders()
                .getFirst("X-Trace-Id");
        Map<String, Object> body = Map.of(
                "code",      code,
                "message",   message,
                "traceId",   traceId != null ? traceId : "",
                "timestamp", System.currentTimeMillis()
        );

        try {
            String json = objectMapper.writeValueAsString(body);
            return ServerResponse.status(HttpStatus.valueOf(code))
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(json);
        } catch (JsonProcessingException e) {
            return ServerResponse.status(HttpStatus.valueOf(code))
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue("{\"code\":" + code + ",\"message\":\"" + message + "\"}");
        }
    }
}
