package com.hd.dr.entity;

import com.baomidou.mybatisplus.annotation.*;

import java.io.Serializable;
import java.time.LocalDateTime;

@TableName("dr_order")
public class DrOrder implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long id;

    /** DR申请单号 */
    @TableField("order_no")
    private String drOrderNo;

    /** 体检单ID */
    private Long checkOrderId;

    /** 居民ID */
    private Long residentId;

    /** 居民姓名 */
    private String residentName;

    /** 身份证号 */
    private String idCard;

    /** 申请机构ID（县级） */
    @TableField(exist = false)
    private Long applyDeptId;

    /** 检查机构ID（有DR设备的机构） */
    @TableField(exist = false)
    private Long checkDeptId;

    /** 条码号（打印后粘贴到申请单） */
    @TableField("barcode")
    private String barcodeNo;

    /** 检查部位：胸部/腹部等 */
    private String bodyPart;

    /** 检查项目描述 */
    @TableField("clinical_info")
    private String description;

    /**
     * 状态：0=待扫码, 1=已扫码/待检查, 2=已完成, 3=已上传, 4=已作废
     */
    private Integer status;

    /** 申请时间 */
    @TableField(exist = false)
    private LocalDateTime applyTime;

    /** 扫码时间 */
    private LocalDateTime scanTime;

    /** 完成时间 */
    @TableField(exist = false)
    private LocalDateTime finishTime;

    /** 申请人ID */
    @TableField("create_doctor_id")
    private Long applyUserId;

    /** 扫码人ID */
    @TableField(exist = false)
    private Long scanUserId;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getDrOrderNo() { return drOrderNo; }
    public void setDrOrderNo(String drOrderNo) { this.drOrderNo = drOrderNo; }
    public Long getCheckOrderId() { return checkOrderId; }
    public void setCheckOrderId(Long checkOrderId) { this.checkOrderId = checkOrderId; }
    public Long getResidentId() { return residentId; }
    public void setResidentId(Long residentId) { this.residentId = residentId; }
    public String getResidentName() { return residentName; }
    public void setResidentName(String residentName) { this.residentName = residentName; }
    public String getIdCard() { return idCard; }
    public void setIdCard(String idCard) { this.idCard = idCard; }
    public Long getApplyDeptId() { return applyDeptId; }
    public void setApplyDeptId(Long applyDeptId) { this.applyDeptId = applyDeptId; }
    public Long getCheckDeptId() { return checkDeptId; }
    public void setCheckDeptId(Long checkDeptId) { this.checkDeptId = checkDeptId; }
    public String getBarcodeNo() { return barcodeNo; }
    public void setBarcodeNo(String barcodeNo) { this.barcodeNo = barcodeNo; }
    public String getBodyPart() { return bodyPart; }
    public void setBodyPart(String bodyPart) { this.bodyPart = bodyPart; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public Integer getStatus() { return status; }
    public void setStatus(Integer status) { this.status = status; }
    public LocalDateTime getApplyTime() { return applyTime; }
    public void setApplyTime(LocalDateTime applyTime) { this.applyTime = applyTime; }
    public LocalDateTime getScanTime() { return scanTime; }
    public void setScanTime(LocalDateTime scanTime) { this.scanTime = scanTime; }
    public LocalDateTime getFinishTime() { return finishTime; }
    public void setFinishTime(LocalDateTime finishTime) { this.finishTime = finishTime; }
    public Long getApplyUserId() { return applyUserId; }
    public void setApplyUserId(Long applyUserId) { this.applyUserId = applyUserId; }
    public Long getScanUserId() { return scanUserId; }
    public void setScanUserId(Long scanUserId) { this.scanUserId = scanUserId; }
    public LocalDateTime getCreateTime() { return createTime; }
    public void setCreateTime(LocalDateTime createTime) { this.createTime = createTime; }
    public LocalDateTime getUpdateTime() { return updateTime; }
    public void setUpdateTime(LocalDateTime updateTime) { this.updateTime = updateTime; }
    public Integer getDeleted() { return deleted; }
    public void setDeleted(Integer deleted) { this.deleted = deleted; }
}
