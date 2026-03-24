package com.health.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 医疗设备
 */
@Data
@TableName("device")
public class Device {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String name;

    private String code;

    private String type;

    private String model;

    private String manufacturer;

    private String serialNo;

    private Long deptId;

    private String ipAddress;

    private Integer port;

    private String protocol;

    /** 状态: ONLINE/OFFLINE/FAULT */
    private String status;

    private LocalDateTime lastHeartbeat;

    private LocalDate calibrationDate;

    private String description;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
