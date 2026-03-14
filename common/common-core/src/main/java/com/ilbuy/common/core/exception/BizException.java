package com.ilbuy.common.core.exception;

import com.ilbuy.common.core.result.ResultCode;
import lombok.Getter;

import java.io.Serial;

/**
 * 业务异常类
 *
 * <p>用于封装所有可预期的业务异常，由GlobalExceptionHandler统一捕获处理。
 * 使用方式：
 * <pre>{@code
 * // 方式1：使用ResultCode枚举
 * throw new BizException(ResultCode.USER_NOT_FOUND);
 *
 * // 方式2：自定义消息
 * throw new BizException(ResultCode.BAD_REQUEST, "手机号格式不正确");
 *
 * // 方式3：自定义码和消息
 * throw new BizException(1001, "用户不存在");
 * }</pre>
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@Getter
public class BizException extends RuntimeException {

    @Serial
    private static final long serialVersionUID = 1L;

    /** 业务错误码 */
    private final int code;

    /** 业务错误描述 */
    private final String message;

    /**
     * 使用ResultCode构造
     *
     * @param resultCode 结果码枚举
     */
    public BizException(ResultCode resultCode) {
        super(resultCode.getMessage());
        this.code = resultCode.getCode();
        this.message = resultCode.getMessage();
    }

    /**
     * 使用ResultCode构造，覆盖默认消息
     *
     * @param resultCode 结果码枚举
     * @param message    自定义错误消息
     */
    public BizException(ResultCode resultCode, String message) {
        super(message);
        this.code = resultCode.getCode();
        this.message = message;
    }

    /**
     * 自定义码和消息
     *
     * @param code    错误码
     * @param message 错误消息
     */
    public BizException(int code, String message) {
        super(message);
        this.code = code;
        this.message = message;
    }

    /**
     * 仅使用错误消息（默认500码）
     *
     * @param message 错误消息
     */
    public BizException(String message) {
        super(message);
        this.code = ResultCode.INTERNAL_ERROR.getCode();
        this.message = message;
    }

    /**
     * 包含原始异常
     *
     * @param resultCode 结果码枚举
     * @param cause      原始异常
     */
    public BizException(ResultCode resultCode, Throwable cause) {
        super(resultCode.getMessage(), cause);
        this.code = resultCode.getCode();
        this.message = resultCode.getMessage();
    }

    // ==================== 静态工厂方法（语义更清晰）====================

    public static BizException of(ResultCode resultCode) {
        return new BizException(resultCode);
    }

    public static BizException of(ResultCode resultCode, String message) {
        return new BizException(resultCode, message);
    }

    public static BizException notFound(String resource) {
        return new BizException(ResultCode.NOT_FOUND, resource + "不存在");
    }

    public static BizException unauthorized() {
        return new BizException(ResultCode.UNAUTHORIZED);
    }

    public static BizException forbidden() {
        return new BizException(ResultCode.FORBIDDEN);
    }
}
