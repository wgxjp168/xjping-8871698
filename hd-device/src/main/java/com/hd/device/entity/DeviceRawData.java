package com.hd.device.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("device_raw_data")
public class DeviceRawData {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long deviceId;

    /**
     * FIX: Removed patient_id from DB column mapping.
     * The database table does not have a 'patient_id' column.
     * If needed in the future, add the column to the DB first,
     * then remove exist=false.
     */
    @TableField(exist = false)
    private Long patientId;

    private String sampleId;

    private String rawMessage;

    private String parsedJson;

    private Integer processStatus;

    private String errorMsg;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
