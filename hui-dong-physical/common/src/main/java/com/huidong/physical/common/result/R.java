package com.huidong.physical.common.result;

import lombok.Data;

import java.io.Serializable;

/**
 * 统一响应结果封装
 */
@Data
public class R<T> implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 状态码 */
    private Integer code;

    /** 提示信息 */
    private String message;

    /** 数据 */
    private T data;

    /** 时间戳 */
    private Long timestamp;

    private R() {
        this.timestamp = System.currentTimeMillis();
    }

    public static <T> R<T> ok() {
        return result(ResultCode.SUCCESS.getCode(), ResultCode.SUCCESS.getMessage(), null);
    }

    public static <T> R<T> ok(T data) {
        return result(ResultCode.SUCCESS.getCode(), ResultCode.SUCCESS.getMessage(), data);
    }

    public static <T> R<T> ok(String message, T data) {
        return result(ResultCode.SUCCESS.getCode(), message, data);
    }

    public static <T> R<T> fail() {
        return result(ResultCode.SYSTEM_ERROR.getCode(), ResultCode.SYSTEM_ERROR.getMessage(), null);
    }

    public static <T> R<T> fail(String message) {
        return result(ResultCode.SYSTEM_ERROR.getCode(), message, null);
    }

    public static <T> R<T> fail(Integer code, String message) {
        return result(code, message, null);
    }

    public static <T> R<T> fail(ResultCode resultCode) {
        return result(resultCode.getCode(), resultCode.getMessage(), null);
    }

    private static <T> R<T> result(Integer code, String message, T data) {
        R<T> r = new R<>();
        r.setCode(code);
        r.setMessage(message);
        r.setData(data);
        return r;
    }

    public boolean isSuccess() {
        return ResultCode.SUCCESS.getCode().equals(this.code);
    }
}
