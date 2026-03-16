package com.ilbuy.gateway.exception;

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
import java.time.Instant;
import java.util.Map;

/**
 * WebFlux 全局异常处理器
 * 捕获路由未匹配 404、下游连接失败 502、限流 429 等
 */
@Component
@Order(-1)          // 优先于 DefaultErrorWebExceptionHandler
@RequiredArgsConstructor
@Slf4j
public class GlobalErrorWebExceptionHandler implements ErrorWebExceptionHandler {

    private final ObjectMapper objectMapper;

    @Override
    public Mono<Void> handle(ServerWebExchange exchange, Throwable ex) {
        ServerHttpResponse response = exchange.getResponse();

        HttpStatus status;
        String message;

        if (ex instanceof ResponseStatusException rse) {
            status  = HttpStatus.resolve(rse.getStatusCode().value());
            if (status == null) status = HttpStatus.INTERNAL_SERVER_ERROR;
            message = rse.getReason() != null ? rse.getReason() : status.getReasonPhrase();
        } else if (ex instanceof java.net.ConnectException) {
            status  = HttpStatus.BAD_GATEWAY;
            message = "下游服务暂时不可达，请稍后重试";
            log.error("Downstream unreachable: {}", ex.getMessage());
        } else if (ex instanceof io.netty.channel.ConnectTimeoutException) {
            status  = HttpStatus.GATEWAY_TIMEOUT;
            message = "下游服务响应超时";
            log.error("Downstream timeout: {}", ex.getMessage());
        } else {
            status  = HttpStatus.INTERNAL_SERVER_ERROR;
            message = "网关内部错误";
            log.error("Gateway unhandled exception", ex);
        }

        response.setStatusCode(status);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);

        Map<String, Object> body = Map.of(
                "timestamp", Instant.now().toString(),
                "status",    status.value(),
                "error",     status.getReasonPhrase(),
                "message",   message,
                "path",      exchange.getRequest().getPath().value()
        );

        byte[] bytes;
        try {
            bytes = objectMapper.writeValueAsBytes(body);
        } catch (JsonProcessingException e) {
            bytes = ("{\"message\":\"" + message + "\"}").getBytes(StandardCharsets.UTF_8);
        }

        DataBuffer buffer = response.bufferFactory().wrap(bytes);
        return response.writeWith(Mono.just(buffer));
    }
}
