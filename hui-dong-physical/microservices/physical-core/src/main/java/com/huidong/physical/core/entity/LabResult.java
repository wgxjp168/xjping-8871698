package com.huidong.physical.core.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.huidong.physical.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

/**
 * 检验结果统一表
 * 支持：生化、血常规、糖化血红蛋白、尿常规
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("t_lab_result")
public class LabResult extends BaseEntity {

    /** 标本ID */
    private Long specimenId;

    /** 体检单ID */
    private Long examRecordId;

    /** 居民ID */
    private Long residentId;

    /** 检验类型 1=生化 2=血常规 3=糖化血红蛋白 4=尿常规 */
    private Integer labType;

    /** 设备编码 */
    private String deviceCode;

    /** 设备类型 */
    private String deviceType;

    /** 检验项目代码（HL7 LOINC码） */
    private String itemCode;

    /** 检验项目名称 */
    private String itemName;

    /** 检验结果值 */
    private String resultValue;

    /** 单位 */
    private String unit;

    /** 参考范围 */
    private String referenceRange;

    /** 结果标志 N=正常 H=偏高 L=偏低 */
    private String resultFlag;

    /** 检验时间 */
    private LocalDateTime labTime;

    /** 原始HL7报文 */
    private String rawHl7Message;

    /** 同步状态 0=待同步 1=已同步 2=失败 */
    private Integer syncStatus;

    /** 来源 1=下乡 2=院内 */
    private Integer sourceType;
}
