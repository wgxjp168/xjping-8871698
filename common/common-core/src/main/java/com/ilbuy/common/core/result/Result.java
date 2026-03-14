package com.ilbuy.common.core.result;

import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Getter;
import lombok.ToString;

import java.io.Serial;
import java.io.Serializable;
import java.time.Instant;

/**
 * 统一API响应结果封装
 *
 * <p>所有Controller接口返回统一使用此类包装，格式：
 * <pre>{@code
 * {
 *   "code": 200,
 *   "message": "操作成功",
 *   "data": {...},
 *   "timestamp": 1710000000000
 * }
 * }</pre>
 *
 * @param <T> 响应数据类型
 * @author ILbuy Team
 * @version 1.0.0
 */
@Getter
@ToString
@Schema(description = "统一响应结果")
@JsonInclude(JsonInclude.Include.NON_NULL)
public class Result<T> implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    /** 响应状态码 */
    @Schema(description = "响应码：200=成功", example = "200")
    private final int code;

    /** 响应描述信息 */
    @Schema(description = "响应描述", example = "操作成功")
    private final String message;

    /** 响应数据 */
    @Schema(description = "响应数据")
    private final T data;

    /** 响应时间戳（毫秒） */
    @Schema(description = "时间戳", example = "1710000000000")
    private final long timestamp;

    private Result(int code, String message, T data) {
        this.code = code;
        this.message = message;
        this.data = data;
        this.timestamp = Instant.now().toEpochMilli();
    }

    // ==================== 成功响应 ====================

    /**
     * 操作成功，无数据
     */
    public static <T> Result<T> ok() {
        return new Result<>(ResultCode.SUCCESS.getCode(), ResultCode.SUCCESS.getMessage(), null);
    }

    /**
     * 操作成功，有数据
     *
     * @param data 响应数据
     */
    public static <T> Result<T> ok(T data) {
        return new Result<>(ResultCode.SUCCESS.getCode(), ResultCode.SUCCESS.getMessage(), data);
    }

    /**
     * 操作成功，自定义消息
     *
     * @param message 成功消息
     * @param data    响应数据
     */
    public static <T> Result<T> ok(String message, T data) {
        return new Result<>(ResultCode.SUCCESS.getCode(), message, data);
    }

    /**
     * 创建成功（HTTP 201）
     *
     * @param data 创建的资源
     */
    public static <T> Result<T> created(T data) {
        return new Result<>(ResultCode.CREATED.getCode(), ResultCode.CREATED.getMessage(), data);
    }

    // ==================== 失败响应 ====================

    /**
     * 操作失败，使用ResultCode
     *
     * @param resultCode 结果码
     */
    public static <T> Result<T> fail(ResultCode resultCode) {
        return new Result<>(resultCode.getCode(), resultCode.getMessage(), null);
    }

    /**
     * 操作失败，自定义消息
     *
     * @param message 错误消息
     */
    public static <T> Result<T> fail(String message) {
        return new Result<>(ResultCode.INTERNAL_ERROR.getCode(), message, null);
    }

    /**
     * 操作失败，自定义码和消息
     *
     * @param code    错误码
     * @param message 错误消息
     */
    public static <T> Result<T> fail(int code, String message) {
        return new Result<>(code, message, null);
    }

    /**
     * 参数错误
     *
     * @param message 参数错误描述
     */
    public static <T> Result<T> badRequest(String message) {
        return new Result<>(ResultCode.BAD_REQUEST.getCode(), message, null);
    }

    /**
     * 未授权（401）
     */
    public static <T> Result<T> unauthorized() {
        return new Result<>(ResultCode.UNAUTHORIZED.getCode(), ResultCode.UNAUTHORIZED.getMessage(), null);
    }

    /**
     * 无权限（403）
     */
    public static <T> Result<T> forbidden() {
        return new Result<>(ResultCode.FORBIDDEN.getCode(), ResultCode.FORBIDDEN.getMessage(), null);
    }

    /**
     * 资源不存在（404）
     */
    public static <T> Result<T> notFound(String message) {
        return new Result<>(ResultCode.NOT_FOUND.getCode(), message, null);
    }

    /**
     * 请求过于频繁（429）
     */
    public static <T> Result<T> tooManyRequests() {
        return new Result<>(ResultCode.TOO_MANY_REQUESTS.getCode(),
                ResultCode.TOO_MANY_REQUESTS.getMessage(), null);
    }

    // ==================== 判断方法 ====================

    /**
     * 判断响应是否成功
     */
    public boolean isSuccess() {
        return this.code == ResultCode.SUCCESS.getCode();
    }

    /**
     * 判断响应是否失败
     */
    public boolean isFail() {
        return !isSuccess();
    }
}
