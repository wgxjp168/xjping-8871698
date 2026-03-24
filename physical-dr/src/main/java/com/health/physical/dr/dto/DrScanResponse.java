package com.health.physical.dr.dto;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * DR条码扫描响应DTO
 * 扫码后返回居民信息和DR申请信息
 */
@Data
@Builder
public class DrScanResponse {

    /** 记录ID */
    private Long id;

    /** DR条码 */
    private String drCode;

    /** 申请单号 */
    private String applyNo;

    /** 居民ID */
    private Long residentId;

    /** 居民姓名 */
    private String residentName;

    /** 身份证号（脱敏） */
    private String idCard;

    /** 性别 */
    private String gender;

    /** 年龄 */
    private Integer age;

    /** 检查部位 */
    private String examPart;

    /** 申请体检批次 */
    private String batchNo;

    /** 状态描述 */
    private String statusDesc;

    /** 是否可进行检查（0-不可，1-可以） */
    private Integer canExam;

    /** 不可检查原因（如已检查、已取消等） */
    private String cannotReason;

    /** 扫码时间 */
    private LocalDateTime scanTime;
}
