package com.huidong.physical.core.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.huidong.physical.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 体检主表
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("t_exam_record")
public class ExamRecord extends BaseEntity {

    /** 体检单号 */
    private String examNo;

    /** 居民ID */
    private Long residentId;

    /** 居民编码 */
    private String residentCode;

    /** 体检类型 1=下乡 2=院内 */
    private Integer examType;

    /** 体检日期 */
    private LocalDate examDate;

    /** 体检地点 */
    private String examLocation;

    /** 体检状态 */
    private Integer examStatus;

    /** 血压-收缩压(mmHg) */
    private Integer systolicPressure;

    /** 血压-舒张压(mmHg) */
    private Integer diastolicPressure;

    /** 体重(kg) */
    private Double weight;

    /** 身高(cm) */
    private Double height;

    /** BMI */
    private Double bmi;

    /** 问诊信息（JSON） */
    private String inquiryInfo;

    /** 同步状态 0=待同步 1=已同步 2=同步失败 */
    private Integer syncStatus;

    /** 同步时间 */
    private LocalDateTime syncTime;

    /** 备注 */
    private String remark;
}
