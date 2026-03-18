package com.ilbuy.common.core.result;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.ilbuy.common.core.enums.ResultCode;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.io.Serial;
import java.io.Serializable;
import java.time.Instant;

/**
 * 统一响应结果封装
 *
 * <pre>{@code
 * // 成功
 * return Result.success(data);
 * // 失败
 * return Result.fail(ResultCode.NOT_FOUND);
 * // 自定义消息
 * return Result.fail(ResultCode.BIZ_ERROR, "具体业务错误信息");
 * }</pre>
 */
@Getter
@NoArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
@Schema(description = "统一响应结果")
public class Result<T> implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Schema(description = "业务状态码", example = "200")
    private int code;

    @Schema(description = "响应消息", example = "操作成功")
    private String message;

    @Schema(description = "响应数据")
    private T data;

    @Schema(description = "服务器时间戳（Unix ms）", example = "1700000000000")
    private long timestamp;

    @Schema(description = "链路追踪 ID")
    private String traceId;

    private Result(int code, String message, T data) {
        this.code    = code;
        this.message = message;
        this.data    = data;
        this.timestamp = Instant.now().toEpochMilli();
    }

    // ──────────────────── 工厂方法 ────────────────────

    public static <T> Result<T> success() {
        return new Result<>(ResultCode.SUCCESS.getCode(), ResultCode.SUCCESS.getMessage(), null);
    }

    public static <T> Result<T> success(T data) {
        return new Result<>(ResultCode.SUCCESS.getCode(), ResultCode.SUCCESS.getMessage(), data);
    }

    public static <T> Result<T> success(String message, T data) {
        return new Result<>(ResultCode.SUCCESS.getCode(), message, data);
    }

    public static <T> Result<T> fail(ResultCode resultCode) {
        return new Result<>(resultCode.getCode(), resultCode.getMessage(), null);
    }

    public static <T> Result<T> fail(ResultCode resultCode, String message) {
        return new Result<>(resultCode.getCode(), message, null);
    }

    public static <T> Result<T> fail(int code, String message) {
        return new Result<>(code, message, null);
    }

    public static <T> Result<T> of(ResultCode resultCode, T data) {
        return new Result<>(resultCode.getCode(), resultCode.getMessage(), data);
    }

    // ──────────────────── 链式方法 ────────────────────

    public Result<T> traceId(String traceId) {
        this.traceId = traceId;
        return this;
    }

    // ──────────────────── 判断方法 ────────────────────

    public boolean isSuccess() {
        return this.code == ResultCode.SUCCESS.getCode();
    }

    public boolean isFail() {
        return !isSuccess();
    }

    @Override
    public String toString() {
        return "Result{code=" + code + ", message='" + message + "', data=" + data + "}";
    }
}
