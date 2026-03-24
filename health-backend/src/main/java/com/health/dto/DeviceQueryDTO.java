package com.health.dto;

import lombok.Data;

/**
 * 设备查询条件
 */
@Data
public class DeviceQueryDTO {

    private String name;
    private String code;
    private String type;
    private String status;
    private Long deptId;
    private Integer pageNum = 1;
    private Integer pageSize = 10;
}
