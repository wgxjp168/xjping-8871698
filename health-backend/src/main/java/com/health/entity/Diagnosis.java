package com.health.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

/**
 * 诊断报告
 */
@Data
@TableName("diagnosis")
public class Diagnosis {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long orderId;

    private Long patientId;

    private Long doctorId;

    private Integer healthScore;

    private String conclusion;

    private String suggestion;

    private String abnormalItems;

    /** 风险等级: LOW/MEDIUM/HIGH */
    private String riskLevel;

    /** 状态: DRAFT/CONFIRMED/PUBLISHED */
    private String status;

    private LocalDateTime confirmTime;

    private LocalDateTime publishTime;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
