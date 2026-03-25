package com.hd.check.entity;

import com.baomidou.mybatisplus.annotation.*;

import java.io.Serializable;
import java.time.LocalDateTime;

@TableName("check_result")
public class CheckResult implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 体检单ID */
    private Long orderId;

    /** 体检单号 */
    private String orderNo;

    /** 居民ID */
    private Long residentId;

    /**
     * 检查类别: BIOCHEM=生化, BLOOD=血常规, URINE=尿常规, HBA1C=糖化血红蛋白, VITAL=体征
     */
    private String category;

    /** 检验项目代码 */
    private String itemCode;

    /** 检验项目名称 */
    private String itemName;

    /** 检验值 */
    private String itemValue;

    /** 单位 */
    private String itemUnit;

    /** 参考范围 */
    private String referenceRange;

    /** 是否异常: 0=正常, 1=偏高, 2=偏低, 3=异常 */
    private Integer abnormalFlag;

    /** 原始设备ID（来自device服务） */
    private Long deviceId;

    /** 原始数据ID */
    private Long rawDataId;

    /** 备注/诊断意见 */
    private String remark;

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
    public String getItemValue() { return itemValue; }
    public void setItemValue(String itemValue) { this.itemValue = itemValue; }
    public String getItemUnit() { return itemUnit; }
    public void setItemUnit(String itemUnit) { this.itemUnit = itemUnit; }
    public String getReferenceRange() { return referenceRange; }
    public void setReferenceRange(String referenceRange) { this.referenceRange = referenceRange; }
    public Integer getAbnormalFlag() { return abnormalFlag; }
    public void setAbnormalFlag(Integer abnormalFlag) { this.abnormalFlag = abnormalFlag; }
    public Long getDeviceId() { return deviceId; }
    public void setDeviceId(Long deviceId) { this.deviceId = deviceId; }
    public Long getRawDataId() { return rawDataId; }
    public void setRawDataId(Long rawDataId) { this.rawDataId = rawDataId; }
    public String getRemark() { return remark; }
    public void setRemark(String remark) { this.remark = remark; }
    public LocalDateTime getCreateTime() { return createTime; }
    public void setCreateTime(LocalDateTime createTime) { this.createTime = createTime; }
    public LocalDateTime getUpdateTime() { return updateTime; }
    public void setUpdateTime(LocalDateTime updateTime) { this.updateTime = updateTime; }
    public Integer getDeleted() { return deleted; }
    public void setDeleted(Integer deleted) { this.deleted = deleted; }
}
