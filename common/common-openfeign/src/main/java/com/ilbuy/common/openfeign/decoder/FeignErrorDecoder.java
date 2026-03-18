package com.ilbuy.common.openfeign.decoder;

import com.ilbuy.common.core.enums.ResultCode;
import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.common.core.result.Result;
import com.ilbuy.common.core.utils.JsonUtils;
import feign.Response;
import feign.codec.ErrorDecoder;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

/**
 * Feign 全局错误解码器
 *
 * <p>将下游服务返回的非 2xx 响应转换为 {@link BizException}，
 * 上层业务代码统一通过 {@link com.ilbuy.common.core.exception.GlobalExceptionHandler} 处理。</p>
 *
 * <p>解码策略：
 * <ul>
 *   <li>401 → TOKEN_INVALID</li>
 *   <li>403 → FORBIDDEN</li>
 *   <li>404 → DATA_NOT_EXIST</li>
 *   <li>4xx → BAD_REQUEST（解析 body 中的 message）</li>
 *   <li>5xx → SERVICE_UNAVAILABLE</li>
 * </ul>
 * </p>
 */
@Slf4j
public class FeignErrorDecoder implements ErrorDecoder {

    @Override
    public Exception decode(String methodKey, Response response) {
        int status = response.status();
        String body = readBody(response);

        log.warn("[FeignErrorDecoder] methodKey={} status={} body={}", methodKey, status, body);

        // 尝试解析下游的 Result JSON，提取 message
        String downstreamMsg = extractMessage(body);

        HttpStatus httpStatus = HttpStatus.resolve(status);
        if (httpStatus == null) {
            return new BizException(ResultCode.INTERNAL_SERVER_ERROR,
                    "下游服务异常 [" + status + "]");
        }

        return switch (httpStatus) {
            case UNAUTHORIZED      -> new BizException(ResultCode.TOKEN_INVALID,
                    downstreamMsg != null ? downstreamMsg : ResultCode.TOKEN_INVALID.getMessage());
            case FORBIDDEN         -> new BizException(ResultCode.FORBIDDEN,
                    downstreamMsg != null ? downstreamMsg : ResultCode.FORBIDDEN.getMessage());
            case NOT_FOUND         -> new BizException(ResultCode.DATA_NOT_EXIST,
                    downstreamMsg != null ? downstreamMsg : "下游资源不存在");
            case TOO_MANY_REQUESTS -> new BizException(ResultCode.TOO_MANY_REQUESTS,
                    downstreamMsg != null ? downstreamMsg : ResultCode.TOO_MANY_REQUESTS.getMessage());
            default -> {
                if (httpStatus.is4xxClientError()) {
                    yield new BizException(ResultCode.BAD_REQUEST,
                            downstreamMsg != null ? downstreamMsg : "下游服务请求错误 [" + status + "]");
                }
                yield new BizException(ResultCode.SERVICE_UNAVAILABLE,
                        "下游服务不可用 [" + methodKey + "] status=" + status);
            }
        };
    }

    private String readBody(Response response) {
        if (response.body() == null) return null;
        try (InputStream is = response.body().asInputStream()) {
            return new String(is.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            log.error("[FeignErrorDecoder] 读取响应体失败", e);
            return null;
        }
    }

    @SuppressWarnings("unchecked")
    private String extractMessage(String body) {
        if (body == null || body.isBlank()) return null;
        try {
            Result<Object> result = JsonUtils.fromJson(body, Result.class);
            return result != null ? result.getMessage() : null;
        } catch (Exception e) {
            return body.length() > 200 ? body.substring(0, 200) + "..." : body;
        }
    }
}
