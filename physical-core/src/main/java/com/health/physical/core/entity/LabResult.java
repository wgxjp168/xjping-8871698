package com.health.physical.core.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 检验结果表（生化/血常规/糖化/尿常规统一存储）
 */
@Data
@TableName("physical_lab_result")
public class LabResult implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 关联体检记录ID */
    @TableField("physical_id")
    private Long physicalId;

    /** 居民ID */
    @TableField("resident_id")
    private Long residentId;

    /** 项目编码：BIOCHEM/CBC/HBA1C/URINE */
    @TableField("project_code")
    private String projectCode;

    /** 检验项目名称 */
    @TableField("project_name")
    private String projectName;

    /** 检验指标编码 */
    @TableField("item_code")
    private String itemCode;

    /** 检验指标名称 */
    @TableField("item_name")
    private String itemName;

    /** 检验结果值 */
    @TableField("result_value")
    private String resultValue;

    /** 结果数值（用于比较） */
    @TableField("result_num")
    private BigDecimal resultNum;

    /** 单位 */
    private String unit;

    /** 参考范围下限 */
    @TableField("ref_low")
    private BigDecimal refLow;

    /** 参考范围上限 */
    @TableField("ref_high")
    private BigDecimal refHigh;

    /** 异常标志：N-正常，L-偏低，H-偏高，C-危急 */
    @TableField("abnormal_flag")
    private String abnormalFlag;

    /** 检验仪器编号 */
    @TableField("device_code")
    private String deviceCode;

    /** 操作员 */
    private String operator;

    /** 检验时间 */
    @TableField("exam_time")
    private LocalDateTime examTime;

    /** 同步状态 */
    @TableField("sync_status")
    private Integer syncStatus;

    /** 状态 */
    private Integer status;

    @TableField(value = "create_time", fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(value = "update_time", fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    @TableField("deleted")
    private Integer deleted;
}
