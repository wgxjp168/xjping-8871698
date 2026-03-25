package com.hd.dr.entity;

import com.baomidou.mybatisplus.annotation.*;

import java.io.Serializable;
import java.time.LocalDateTime;

@TableName("dr_report")
public class DrReport implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long id;

    /** DR申请单ID */
    private Long drOrderId;

    /** 报告编号 */
    private String reportNo;

    /** 影像所见 */
    private String findings;

    /** 诊断意见 */
    private String diagnosis;

    /** 影像文件路径（相对路径） */
    private String imagePath;

    /** 报告PDF路径 */
    private String reportPath;

    /** 报告医生ID */
    private Long reportDoctorId;

    /** 报告时间 */
    private LocalDateTime reportTime;

    /**
     * 上传状态: 0=未上传, 1=已上传到平台, 2=上传失败
     */
    private Integer uploadStatus;

    /** 上传时间 */
    private LocalDateTime uploadTime;

    /** 上传错误信息 */
    private String uploadError;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getDrOrderId() { return drOrderId; }
    public void setDrOrderId(Long drOrderId) { this.drOrderId = drOrderId; }
    public String getReportNo() { return reportNo; }
    public void setReportNo(String reportNo) { this.reportNo = reportNo; }
    public String getFindings() { return findings; }
    public void setFindings(String findings) { this.findings = findings; }
    public String getDiagnosis() { return diagnosis; }
    public void setDiagnosis(String diagnosis) { this.diagnosis = diagnosis; }
    public String getImagePath() { return imagePath; }
    public void setImagePath(String imagePath) { this.imagePath = imagePath; }
    public String getReportPath() { return reportPath; }
    public void setReportPath(String reportPath) { this.reportPath = reportPath; }
    public Long getReportDoctorId() { return reportDoctorId; }
    public void setReportDoctorId(Long reportDoctorId) { this.reportDoctorId = reportDoctorId; }
    public LocalDateTime getReportTime() { return reportTime; }
    public void setReportTime(LocalDateTime reportTime) { this.reportTime = reportTime; }
    public Integer getUploadStatus() { return uploadStatus; }
    public void setUploadStatus(Integer uploadStatus) { this.uploadStatus = uploadStatus; }
    public LocalDateTime getUploadTime() { return uploadTime; }
    public void setUploadTime(LocalDateTime uploadTime) { this.uploadTime = uploadTime; }
    public String getUploadError() { return uploadError; }
    public void setUploadError(String uploadError) { this.uploadError = uploadError; }
    public LocalDateTime getCreateTime() { return createTime; }
    public void setCreateTime(LocalDateTime createTime) { this.createTime = createTime; }
    public LocalDateTime getUpdateTime() { return updateTime; }
    public void setUpdateTime(LocalDateTime updateTime) { this.updateTime = updateTime; }
    public Integer getDeleted() { return deleted; }
    public void setDeleted(Integer deleted) { this.deleted = deleted; }
}
