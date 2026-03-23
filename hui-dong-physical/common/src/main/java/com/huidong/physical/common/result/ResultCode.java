package com.huidong.physical.common.result;

import lombok.AllArgsConstructor;
import lombok.Getter;

/**
 * 统一响应状态码
 */
@Getter
@AllArgsConstructor
public enum ResultCode {

    SUCCESS(200, "操作成功"),
    BAD_REQUEST(400, "请求参数错误"),
    UNAUTHORIZED(401, "未授权"),
    FORBIDDEN(403, "禁止访问"),
    NOT_FOUND(404, "资源不存在"),
    SYSTEM_ERROR(500, "系统内部错误"),

    // 业务错误码 1xxx
    RESIDENT_NOT_FOUND(1001, "居民信息不存在"),
    EXAM_RECORD_NOT_FOUND(1002, "体检记录不存在"),
    SPECIMEN_NOT_FOUND(1003, "标本不存在"),
    DUPLICATE_SPECIMEN(1004, "标本已关联，不可重复绑定"),
    EXAM_ALREADY_COMPLETED(1005, "体检已完成，不可修改"),

    // 设备错误码 2xxx
    DEVICE_NOT_FOUND(2001, "设备不存在"),
    DEVICE_OFFLINE(2002, "设备离线"),
    PROTOCOL_PARSE_ERROR(2003, "协议解析失败"),
    HL7_PARSE_ERROR(2004, "HL7报文解析失败"),

    // 同步错误码 3xxx
    SYNC_FAILED(3001, "上报县域平台失败"),
    SYNC_RETRY_EXHAUSTED(3002, "上报重试次数耗尽"),
    SYNC_DATA_INVALID(3003, "上报数据格式不合法");

    private final Integer code;
    private final String message;
}
