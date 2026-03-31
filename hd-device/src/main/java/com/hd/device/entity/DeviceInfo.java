package com.hd.device.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("device_info")
public class DeviceInfo {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("device_code")
    private String deviceNo;

    private String deviceName;

    private String deviceModel;

    private String manufacturer;

    @TableField("category")
    private String deviceType;

    private String protocol;

    private Long deptId;

    @TableField("comm_host")
    private String ipAddress;

    @TableField("comm_port")
    private Integer port;

    private Integer baudRate;

    @TableField("comm_type")
    private String connectMode;

    /**
     * FIX: status column stores string values like "ONLINE", "OFFLINE" in the database.
     * Changed from Integer to String to match the actual DB column type.
     */
    private String status;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
