package com.hd.device.entity;

import com.baomidou.mybatisplus.annotation.*;

import java.io.Serializable;
import java.time.LocalDateTime;

@TableName("device_info")
public class DeviceInfo implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 设备编号 */
    @TableField("device_code")
    private String deviceNo;

    /** 设备名称 */
    private String deviceName;

    /** 设备型号 */
    private String deviceModel;

    /** 设备厂家 */
    private String manufacturer;

    /**
     * 设备类型: BIOCHEM=生化, BLOOD=血常规, URINE=尿常规, HBA1C=糖化血红蛋白
     */
    @TableField("category")
    private String deviceType;

    /**
     * 协议类型: ASTM=ASTM E1394, MINDRAY=迈瑞自定义
     */
    private String protocol;

    /** 所属机构ID */
    private Long deptId;

    /** 设备IP地址（主动上传模式下填写） */
    @TableField("comm_host")
    private String ipAddress;

    /** 设备端口（TCP模式）或COM口号（串口模式） */
    @TableField("comm_port")
    private Integer port;

    /** 串口波特率（串口模式，默认9600） */
    @TableField("baud_rate")
    private Integer baudRate;

    /**
     * 连接模式: TCP_SERVER=TCP监听, TCP_CLIENT=TCP主动
     */
    @TableField("comm_type")
    private String connectMode;

    /** 状态：0=离线, 1=在线 */
    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getDeviceNo() { return deviceNo; }
    public void setDeviceNo(String deviceNo) { this.deviceNo = deviceNo; }
    public String getDeviceName() { return deviceName; }
    public void setDeviceName(String deviceName) { this.deviceName = deviceName; }
    public String getDeviceModel() { return deviceModel; }
    public void setDeviceModel(String deviceModel) { this.deviceModel = deviceModel; }
    public String getManufacturer() { return manufacturer; }
    public void setManufacturer(String manufacturer) { this.manufacturer = manufacturer; }
    public String getDeviceType() { return deviceType; }
    public void setDeviceType(String deviceType) { this.deviceType = deviceType; }
    public String getProtocol() { return protocol; }
    public void setProtocol(String protocol) { this.protocol = protocol; }
    public Long getDeptId() { return deptId; }
    public void setDeptId(Long deptId) { this.deptId = deptId; }
    public String getIpAddress() { return ipAddress; }
    public void setIpAddress(String ipAddress) { this.ipAddress = ipAddress; }
    public Integer getPort() { return port; }
    public void setPort(Integer port) { this.port = port; }
    public Integer getBaudRate() { return baudRate; }
    public void setBaudRate(Integer baudRate) { this.baudRate = baudRate; }
    public String getConnectMode() { return connectMode; }
    public void setConnectMode(String connectMode) { this.connectMode = connectMode; }
    public Integer getStatus() { return status; }
    public void setStatus(Integer status) { this.status = status; }
    public LocalDateTime getCreateTime() { return createTime; }
    public void setCreateTime(LocalDateTime createTime) { this.createTime = createTime; }
    public LocalDateTime getUpdateTime() { return updateTime; }
    public void setUpdateTime(LocalDateTime updateTime) { this.updateTime = updateTime; }
    public Integer getDeleted() { return deleted; }
    public void setDeleted(Integer deleted) { this.deleted = deleted; }
}
