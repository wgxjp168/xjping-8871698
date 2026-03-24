package com.health.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 体检单
 */
@Data
@TableName("check_order")
public class CheckOrder {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String orderNo;

    private Long patientId;

    private Long appointmentId;

    private Long packageId;

    private LocalDate checkDate;

    private Long doctorId;

    /** 状态: CREATED/IN_PROGRESS/REVIEWING/COMPLETED */
    private String status;

    private Integer totalScore;

    private String summary;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
