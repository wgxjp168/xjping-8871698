package com.hd.device.entity;

import com.baomidou.mybatisplus.annotation.*;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 检验结果实体（跨模块写入 check_result 表）
 * 字段映射对应实际DB列名
 */
@TableName("check_result")
public class DeviceCheckResult implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 体检单ID */
    private Long orderId;

    /** 体检单号 */
    private String orderNo;

    /** 居民ID */
    private Long residentId;

    /** 检查类别: BIOCHEM/BLOOD/URINE/HBA1C */
    private String category;

    /** 检验项目编码（公卫标准编码） */
    private String itemCode;

    /** 检验项目名称 */
    private String itemName;

    /** 结果文本 */
    @TableField("value_str")
    private String valueStr;

    /** 数值结果 */
    @TableField("value_num")
    private BigDecimal valueNum;

    /** 单位 */
    @TableField("unit")
    private String unit;

    /** 参考范围 */
    @TableField("ref_range")
    private String refRange;

    /** 标志: H=偏高, L=偏低, N=正常, A=异常 */
    @TableField("flag")
    private String flag;

    /** 设备ID */
    private Long deviceId;

    /** 设备编码 */
    private String deviceCode;

    /** 设备型号 */
    private String deviceModel;

    /** 数据来源: DEVICE=设备上传, MANUAL=手工录入 */
    private String dataSource;

    /** 样本号（来自设备） */
    private String sampleId;

    /** 检验时间 */
    private LocalDateTime checkTime;

    /** 上传状态: 0=未上传, 1=已上传 */
    private Integer uploadStatus;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getOrderId() { return orderId; }
    public void setOrderId(Long orderId) { this.orderId = orderId; }
    public String getOrderNo() { return orderNo; }
    public void setOrderNo(String orderNo) { this.orderNo = orderNo; }
    public Long getResidentId() { return residentId; }
    public void setResidentId(Long residentId) { this.residentId = residentId; }
    public String getCategory() { return category; }
    public void setCategory(String category) { this.category = category; }
    public String getItemCode() { return itemCode; }
    public void setItemCode(String itemCode) { this.itemCode = itemCode; }
    public String getItemName() { return itemName; }
    public void setItemName(String itemName) { this.itemName = itemName; }
    public String getValueStr() { return valueStr; }
    public void setValueStr(String valueStr) { this.valueStr = valueStr; }
    public BigDecimal getValueNum() { return valueNum; }
    public void setValueNum(BigDecimal valueNum) { this.valueNum = valueNum; }
    public String getUnit() { return unit; }
    public void setUnit(String unit) { this.unit = unit; }
    public String getRefRange() { return refRange; }
    public void setRefRange(String refRange) { this.refRange = refRange; }
    public String getFlag() { return flag; }
    public void setFlag(String flag) { this.flag = flag; }
    public Long getDeviceId() { return deviceId; }
    public void setDeviceId(Long deviceId) { this.deviceId = deviceId; }
    public String getDeviceCode() { return deviceCode; }
    public void setDeviceCode(String deviceCode) { this.deviceCode = deviceCode; }
    public String getDeviceModel() { return deviceModel; }
    public void setDeviceModel(String deviceModel) { this.deviceModel = deviceModel; }
    public String getDataSource() { return dataSource; }
    public void setDataSource(String dataSource) { this.dataSource = dataSource; }
    public String getSampleId() { return sampleId; }
    public void setSampleId(String sampleId) { this.sampleId = sampleId; }
    public LocalDateTime getCheckTime() { return checkTime; }
    public void setCheckTime(LocalDateTime checkTime) { this.checkTime = checkTime; }
    public Integer getUploadStatus() { return uploadStatus; }
    public void setUploadStatus(Integer uploadStatus) { this.uploadStatus = uploadStatus; }
    public LocalDateTime getCreateTime() { return createTime; }
    public void setCreateTime(LocalDateTime createTime) { this.createTime = createTime; }
    public LocalDateTime getUpdateTime() { return updateTime; }
    public void setUpdateTime(LocalDateTime updateTime) { this.updateTime = updateTime; }
    public Integer getDeleted() { return deleted; }
    public void setDeleted(Integer deleted) { this.deleted = deleted; }
}
