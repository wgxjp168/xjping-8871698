package com.ilbuy.gateway.api.handler;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.web.reactive.error.ErrorWebExceptionHandler;
import org.springframework.core.annotation.Order;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 网关全局异常处理器
 *
 * <p>拦截所有未被路由/过滤器处理的异常，统一返回 JSON 响应。</p>
 *
 * <p>优先级 -1（高于 Spring 默认的 DefaultErrorWebExceptionHandler）。</p>
 */
@Slf4j
@Order(-1)
@Component
@RequiredArgsConstructor
public class GatewayExceptionHandler implements ErrorWebExceptionHandler {

    private final ObjectMapper objectMapper;

    @Override
    public Mono<Void> handle(ServerWebExchange exchange, Throwable ex) {
        ServerHttpResponse response = exchange.getResponse();

        if (response.isCommitted()) {
            return Mono.error(ex);
        }

        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);

        HttpStatus status;
        String message;

        if (ex instanceof ResponseStatusException rse) {
            status  = HttpStatus.valueOf(rse.getStatusCode().value());
            message = rse.getReason() != null ? rse.getReason() : rse.getMessage();
        } else if (ex instanceof io.netty.channel.ConnectTimeoutException
                || ex instanceof java.net.ConnectException) {
            status  = HttpStatus.SERVICE_UNAVAILABLE;
            message = "下游服务连接超时，请稍后重试";
            log.warn("[Gateway] 连接超时 path={} err={}", exchange.getRequest().getPath().value(), ex.getMessage());
        } else {
            status  = HttpStatus.INTERNAL_SERVER_ERROR;
            message = "网关内部错误";
            log.error("[Gateway] 未知异常 path={}", exchange.getRequest().getPath().value(), ex);
        }

        response.setStatusCode(status);

        String traceId = exchange.getResponse().getHeaders().getFirst("X-Trace-Id");

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("code",      status.value());
        body.put("message",   message);
        body.put("traceId",   traceId != null ? traceId : "");
        body.put("timestamp", System.currentTimeMillis());

        byte[] bytes;
        try {
            bytes = objectMapper.writeValueAsBytes(body);
        } catch (JsonProcessingException e) {
            bytes = ("{\"code\":" + status.value() + ",\"message\":\"" + message + "\"}")
                    .getBytes(StandardCharsets.UTF_8);
        }

        DataBuffer buffer = response.bufferFactory().wrap(bytes);
        return response.writeWith(Mono.just(buffer));
    }
}
