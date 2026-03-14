package com.ilbuy.common.core.exception;

import com.ilbuy.common.core.result.Result;
import com.ilbuy.common.core.result.ResultCode;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.ConstraintViolationException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.validation.BindException;
import org.springframework.validation.FieldError;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;

import java.util.stream.Collectors;

/**
 * 全局异常统一处理器
 *
 * <p>处理优先级（从高到低）：
 * <ol>
 *   <li>BizException - 业务异常</li>
 *   <li>参数校验异常（Validation）</li>
 *   <li>Spring MVC 异常</li>
 *   <li>兜底 Exception</li>
 * </ol>
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    // ==================== 业务异常 ====================

    /**
     * 处理业务异常
     */
    @ExceptionHandler(BizException.class)
    public Result<Void> handleBizException(BizException e, HttpServletRequest request) {
        log.warn("[BizException] URI={}, code={}, msg={}",
                request.getRequestURI(), e.getCode(), e.getMessage());
        return Result.fail(e.getCode(), e.getMessage());
    }

    // ==================== 参数校验异常 ====================

    /**
     * 处理 @RequestBody @Valid 校验失败
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleMethodArgumentNotValid(
            MethodArgumentNotValidException e, HttpServletRequest request) {
        String message = e.getBindingResult().getFieldErrors()
                .stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining("; "));
        log.warn("[ValidationException] URI={}, errors={}", request.getRequestURI(), message);
        return Result.badRequest(message);
    }

    /**
     * 处理 @RequestParam @PathVariable 等参数校验失败
     */
    @ExceptionHandler(ConstraintViolationException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleConstraintViolation(
            ConstraintViolationException e, HttpServletRequest request) {
        String message = e.getConstraintViolations()
                .stream()
                .map(ConstraintViolation::getMessage)
                .collect(Collectors.joining("; "));
        log.warn("[ConstraintViolation] URI={}, errors={}", request.getRequestURI(), message);
        return Result.badRequest(message);
    }

    /**
     * 处理 Form表单参数绑定失败
     */
    @ExceptionHandler(BindException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleBindException(BindException e, HttpServletRequest request) {
        String message = e.getFieldErrors()
                .stream()
                .map(f -> f.getField() + ": " + f.getDefaultMessage())
                .collect(Collectors.joining("; "));
        log.warn("[BindException] URI={}, errors={}", request.getRequestURI(), message);
        return Result.badRequest(message);
    }

    /**
     * 处理请求参数缺失
     */
    @ExceptionHandler(MissingServletRequestParameterException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleMissingParam(
            MissingServletRequestParameterException e, HttpServletRequest request) {
        String message = "缺少必要参数: " + e.getParameterName();
        log.warn("[MissingParam] URI={}, param={}", request.getRequestURI(), e.getParameterName());
        return Result.badRequest(message);
    }

    /**
     * 处理参数类型不匹配
     */
    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleTypeMismatch(
            MethodArgumentTypeMismatchException e, HttpServletRequest request) {
        String message = "参数类型错误: " + e.getName() + " 应为 " +
                (e.getRequiredType() != null ? e.getRequiredType().getSimpleName() : "正确类型");
        log.warn("[TypeMismatch] URI={}, param={}", request.getRequestURI(), e.getName());
        return Result.badRequest(message);
    }

    // ==================== Spring MVC 异常 ====================

    /**
     * 处理请求方法不支持（405）
     */
    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    @ResponseStatus(HttpStatus.METHOD_NOT_ALLOWED)
    public Result<Void> handleMethodNotSupported(
            HttpRequestMethodNotSupportedException e, HttpServletRequest request) {
        log.warn("[MethodNotAllowed] URI={}, method={}", request.getRequestURI(), e.getMethod());
        return Result.fail(ResultCode.METHOD_NOT_ALLOWED);
    }

    /**
     * 处理文件上传超大（413）
     */
    @ExceptionHandler(MaxUploadSizeExceededException.class)
    @ResponseStatus(HttpStatus.PAYLOAD_TOO_LARGE)
    public Result<Void> handleMaxUploadSize(
            MaxUploadSizeExceededException e, HttpServletRequest request) {
        log.warn("[FileTooLarge] URI={}", request.getRequestURI());
        return Result.fail(413, "上传文件超过大小限制");
    }

    // ==================== 兜底异常 ====================

    /**
     * 处理所有未捕获异常（兜底）
     */
    @ExceptionHandler(Exception.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public Result<Void> handleException(Exception e, HttpServletRequest request) {
        log.error("[UnhandledException] URI={}, error={}", request.getRequestURI(), e.getMessage(), e);
        return Result.fail(ResultCode.INTERNAL_ERROR);
    }
}
