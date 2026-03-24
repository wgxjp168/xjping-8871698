package com.health.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

/**
 * 设备采集数据
 */
@Data
@TableName("device_data")
public class DeviceData {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long deviceId;

    private String deviceCode;

    private Long orderId;

    private Long patientId;

    private String itemCode;

    private String value;

    private String unit;

    private String rawData;

    private LocalDateTime measureTime;

    /** 状态: PENDING/CONFIRMED/INVALID */
    private String status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
