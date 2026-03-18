package com.ilbuy.common.core.exception;

import com.ilbuy.common.core.enums.ResultCode;
import com.ilbuy.common.core.result.Result;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.ConstraintViolationException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.BindException;
import org.springframework.validation.FieldError;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import java.util.stream.Collectors;

/**
 * 全局异常处理器
 *
 * <p>覆盖范围：
 * <ul>
 *   <li>BizException：业务异常</li>
 *   <li>MethodArgumentNotValidException：@Valid 参数校验失败</li>
 *   <li>ConstraintViolationException：@Validated 方法参数校验失败</li>
 *   <li>BindException：表单绑定失败</li>
 *   <li>NoResourceFoundException：404</li>
 *   <li>HttpRequestMethodNotSupportedException：405</li>
 *   <li>Exception：兜底</li>
 * </ul>
 * </p>
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    // ──── 业务异常（不打印堆栈，避免日志污染） ────

    @ExceptionHandler(BizException.class)
    @ResponseStatus(HttpStatus.OK)
    public Result<Void> handleBizException(BizException e, HttpServletRequest req) {
        log.warn("[BizException] uri={} code={} msg={}", req.getRequestURI(), e.getCode(), e.getMessage());
        return Result.fail(e.getCode(), e.getMessage());
    }

    // ──── @Valid / @RequestBody 参数校验失败 ────

    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleValidationException(MethodArgumentNotValidException e) {
        String msg = e.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining("; "));
        log.warn("[ValidationException] {}", msg);
        return Result.fail(ResultCode.BAD_REQUEST, msg);
    }

    // ──── @Validated 方法参数（非 Bean） ────

    @ExceptionHandler(ConstraintViolationException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleConstraintViolation(ConstraintViolationException e) {
        String msg = e.getConstraintViolations().stream()
                .map(ConstraintViolation::getMessage)
                .collect(Collectors.joining("; "));
        log.warn("[ConstraintViolation] {}", msg);
        return Result.fail(ResultCode.BAD_REQUEST, msg);
    }

    // ──── 表单绑定失败 ────

    @ExceptionHandler(BindException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleBindException(BindException e) {
        String msg = e.getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining("; "));
        log.warn("[BindException] {}", msg);
        return Result.fail(ResultCode.BAD_REQUEST, msg);
    }

    // ──── 缺少必填请求参数 ────

    @ExceptionHandler(MissingServletRequestParameterException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleMissingParam(MissingServletRequestParameterException e) {
        String msg = "缺少必填参数: " + e.getParameterName();
        log.warn("[MissingParam] {}", msg);
        return Result.fail(ResultCode.BAD_REQUEST, msg);
    }

    // ──── 请求体不可读（JSON 格式错误） ────

    @ExceptionHandler(HttpMessageNotReadableException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleNotReadable(HttpMessageNotReadableException e) {
        log.warn("[NotReadable] {}", e.getMessage());
        return Result.fail(ResultCode.BAD_REQUEST, "请求体格式错误");
    }

    // ──── 参数类型不匹配 ────

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleTypeMismatch(MethodArgumentTypeMismatchException e) {
        String msg = String.format("参数 '%s' 类型错误，期望类型：%s", e.getName(),
                e.getRequiredType() != null ? e.getRequiredType().getSimpleName() : "unknown");
        log.warn("[TypeMismatch] {}", msg);
        return Result.fail(ResultCode.BAD_REQUEST, msg);
    }

    // ──── 404 ────

    @ExceptionHandler(NoResourceFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public Result<Void> handleNotFound(NoResourceFoundException e) {
        return Result.fail(ResultCode.NOT_FOUND, e.getMessage());
    }

    // ──── 405 ────

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    @ResponseStatus(HttpStatus.METHOD_NOT_ALLOWED)
    public Result<Void> handleMethodNotAllowed(HttpRequestMethodNotSupportedException e) {
        return Result.fail(ResultCode.METHOD_NOT_ALLOWED, e.getMessage());
    }

    // ──── 兜底：未预期异常（打印完整堆栈） ────

    @ExceptionHandler(Exception.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public Result<Void> handleException(Exception e, HttpServletRequest req) {
        log.error("[UnexpectedException] uri={}", req.getRequestURI(), e);
        return Result.fail(ResultCode.INTERNAL_SERVER_ERROR);
    }
}
