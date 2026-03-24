package com.health.dto;

import lombok.Data;
import javax.validation.constraints.NotBlank;
import java.time.LocalDate;

/**
 * 设备保存/更新请求
 */
@Data
public class DeviceSaveDTO {

    private Long id;

    @NotBlank(message = "设备名称不能为空")
    private String name;

    @NotBlank(message = "设备编码不能为空")
    private String code;

    private String type;
    private String model;
    private String manufacturer;
    private String serialNo;
    private Long deptId;
    private String ipAddress;
    private Integer port;
    private String protocol;
    private LocalDate calibrationDate;
    private String description;
}
