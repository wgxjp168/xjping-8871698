package com.health.vo;

import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 设备视图对象
 */
@Data
public class DeviceVO {

    private Long id;
    private String name;
    private String code;
    private String type;
    private String typeName;
    private String model;
    private String manufacturer;
    private String serialNo;
    private Long deptId;
    private String deptName;
    private String ipAddress;
    private Integer port;
    private String protocol;
    private String status;
    private String statusName;
    private LocalDateTime lastHeartbeat;
    private LocalDate calibrationDate;
    private String description;
    private LocalDateTime createTime;
}
