package com.huidong.physical.core.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.huidong.physical.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

/**
 * 标本表
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("t_specimen")
public class Specimen extends BaseEntity {

    /** 标本编号 */
    private String specimenNo;

    /** 体检单ID */
    private Long examRecordId;

    /** 居民ID */
    private Long residentId;

    /** 标本类型 1=血液 2=尿液 3=糖化 */
    private Integer specimenType;

    /** 采集地点 1=下乡 2=院内 */
    private Integer collectLocation;

    /** 采集时间 */
    private LocalDateTime collectTime;

    /** 采集人 */
    private String collectBy;

    /** 标本状态 0=待检 1=检验中 2=已完成 3=作废 */
    private Integer specimenStatus;

    /** 条码号（扫码枪扫出的条码） */
    private String barcodeNo;

    /** 备注 */
    private String remark;
}
