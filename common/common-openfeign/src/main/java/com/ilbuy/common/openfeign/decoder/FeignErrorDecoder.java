package com.ilbuy.common.openfeign.decoder;

import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.common.core.result.Result;
import com.ilbuy.common.core.result.ResultCode;
import com.ilbuy.common.core.utils.JsonUtils;
import feign.Response;
import feign.codec.ErrorDecoder;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.io.IOUtils;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * Feign 错误响应解码器
 *
 * <p>将下游服务返回的错误响应（4xx/5xx）解码为 BizException，
 * 避免将原始FeignException暴露给上层业务代码。
 *
 * <p>处理逻辑：
 * <ol>
 *   <li>4xx错误：解析响应体中的Result，抛出对应BizException</li>
 *   <li>5xx错误：抛出服务不可用异常（触发熔断降级）</li>
 *   <li>无法解析时：抛出通用系统异常</li>
 * </ol>
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@Slf4j
public class FeignErrorDecoder implements ErrorDecoder {

    private final ErrorDecoder defaultDecoder = new ErrorDecoder.Default();

    @Override
    public Exception decode(String methodKey, Response response) {
        int status = response.status();
        String responseBody = readResponseBody(response);

        log.warn("[FeignError] 下游服务响应异常: method={}, status={}, body={}",
                methodKey, status, responseBody);

        // 尝试解析为标准Result格式
        if (responseBody != null) {
            Result<?> result = JsonUtils.fromJson(responseBody, Result.class);
            if (result != null && result.getCode() != 200) {
                return new BizException(result.getCode(), result.getMessage());
            }
        }

        // 按HTTP状态码处理
        return switch (status) {
            case 400 -> new BizException(ResultCode.BAD_REQUEST);
            case 401 -> new BizException(ResultCode.UNAUTHORIZED);
            case 403 -> new BizException(ResultCode.FORBIDDEN);
            case 404 -> new BizException(ResultCode.NOT_FOUND);
            case 429 -> new BizException(ResultCode.TOO_MANY_REQUESTS);
            case 503 -> new BizException(ResultCode.SERVICE_UNAVAILABLE);
            default -> status >= 500
                    ? new BizException(ResultCode.INTERNAL_ERROR)
                    : defaultDecoder.decode(methodKey, response);
        };
    }

    private String readResponseBody(Response response) {
        if (response.body() == null) {
            return null;
        }
        try {
            return IOUtils.toString(response.body().asInputStream(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            log.warn("[FeignError] 读取响应体失败", e);
            return null;
        }
    }
}
