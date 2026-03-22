package com.ilbuy.shop.common;

import lombok.Data;

/**
 * 统一响应封装
 */
@Data
public class Result<T> {

    private int code;
    private String msg;
    private T data;

    private Result() {}

    public static <T> Result<T> ok(T data) {
        Result<T> r = new Result<>();
        r.code = 200;
        r.msg  = "success";
        r.data = data;
        return r;
    }

    public static <T> Result<T> ok() {
        return ok(null);
    }

    public static <T> Result<T> fail(String msg) {
        Result<T> r = new Result<>();
        r.code = 500;
        r.msg  = msg;
        return r;
    }

    public static <T> Result<T> fail(int code, String msg) {
        Result<T> r = new Result<>();
        r.code = code;
        r.msg  = msg;
        return r;
    }
}
