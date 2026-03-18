package com.ilbuy.common.core.exception;

import com.ilbuy.common.core.enums.ResultCode;
import lombok.Getter;

import java.io.Serial;

/**
 * 业务异常（受控异常，框架层统一捕获，不打印堆栈）
 *
 * <pre>{@code
 * throw new BizException(ResultCode.USER_NOT_FOUND);
 * throw new BizException(ResultCode.BIZ_ERROR, "订单 {} 不存在", orderId);
 * }</pre>
 */
@Getter
public class BizException extends RuntimeException {

    @Serial
    private static final long serialVersionUID = 1L;

    private final int code;
    private final String message;

    public BizException(ResultCode resultCode) {
        super(resultCode.getMessage(), null, true, false); // 不记录堆栈，提升性能
        this.code    = resultCode.getCode();
        this.message = resultCode.getMessage();
    }

    public BizException(ResultCode resultCode, String message) {
        super(message, null, true, false);
        this.code    = resultCode.getCode();
        this.message = message;
    }

    public BizException(ResultCode resultCode, String format, Object... args) {
        this(resultCode, String.format(format.replace("{}", "%s"), args));
    }

    public BizException(int code, String message) {
        super(message, null, true, false);
        this.code    = code;
        this.message = message;
    }

    /**
     * 静态工厂：断言不为 null，为 null 时抛异常
     */
    public static void notNull(Object obj, ResultCode resultCode) {
        if (obj == null) {
            throw new BizException(resultCode);
        }
    }

    /**
     * 静态工厂：断言条件为 true，否则抛异常
     */
    public static void isTrue(boolean condition, ResultCode resultCode) {
        if (!condition) {
            throw new BizException(resultCode);
        }
    }

    /**
     * 静态工厂：断言条件为 true，否则抛带自定义消息的异常
     */
    public static void isTrue(boolean condition, ResultCode resultCode, String message) {
        if (!condition) {
            throw new BizException(resultCode, message);
        }
    }
}
