package com.huidong.physical.core.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.huidong.physical.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

/**
 * 设备信息表
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("t_device")
public class Device extends BaseEntity {

    /** 设备编码 */
    private String deviceCode;

    /** 设备名称 */
    private String deviceName;

    /** 设备类型（对应DeviceTypeEnum） */
    private String deviceType;

    /** 设备型号 */
    private String deviceModel;

    /** 厂商 */
    private String manufacturer;

    /** 连接方式 SERIAL=串口 TCP=网口 HL7=HL7标准 */
    private String connectType;

    /** IP地址（网口/HL7） */
    private String ipAddress;

    /** 端口 */
    private Integer port;

    /** 串口号（串口设备） */
    private String serialPort;

    /** 使用位置 1=下乡 2=院内 */
    private Integer location;

    /** 在线状态 0=离线 1=在线 */
    private Integer onlineStatus;

    /** 最后心跳时间 */
    private LocalDateTime lastHeartbeat;

    /** 是否启用 */
    private Integer enabled;

    /** 备注 */
    private String remark;
}
