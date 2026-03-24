package com.health.physical.common.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 体检记录表
 */
@Data
@TableName("physical_record")
public class PhysicalRecord implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 居民ID */
    @TableField("resident_id")
    private Long residentId;

    /** 体检日期 */
    @TableField("exam_date")
    private LocalDate examDate;

    /** 体检批次号 */
    @TableField("batch_no")
    private String batchNo;

    /** 组织单位（乡镇/村） */
    @TableField("org_name")
    private String orgName;

    /** 体重(kg) */
    private BigDecimal weight;

    /** 身高(cm) */
    private BigDecimal height;

    /** 体重指数BMI */
    private BigDecimal bmi;

    /** 收缩压(mmHg) */
    @TableField("systolic_bp")
    private Integer systolicBp;

    /** 舒张压(mmHg) */
    @TableField("diastolic_bp")
    private Integer diastolicBp;

    /** 同步状态：0-未同步，1-已同步，2-同步失败 */
    @TableField("sync_status")
    private Integer syncStatus;

    /** 县域体检ID */
    @TableField("county_physical_id")
    private String countyPhysicalId;

    /** 状态：1-进行中，2-已完成，3-已取消 */
    private Integer status;

    /** 录入操作员 */
    @TableField("operator")
    private String operator;

    @TableField(value = "create_time", fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(value = "update_time", fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    @TableField("deleted")
    private Integer deleted;
}
