package com.health.physical.dr.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * DR检查记录表
 */
@Data
@TableName("physical_dr_record")
public class DrRecord implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long id;

    /** DR条码（县域系统打印，全局唯一） */
    @TableField("dr_code")
    private String drCode;

    /** 居民ID */
    @TableField("resident_id")
    private Long residentId;

    /** 居民姓名 */
    @TableField("resident_name")
    private String residentName;

    /** 居民身份证号 */
    @TableField("id_card")
    private String idCard;

    /** 关联体检单ID */
    @TableField("physical_id")
    private Long physicalId;

    /** DR检查申请单号（县域生成） */
    @TableField("apply_no")
    private String applyNo;

    /** 检查部位 */
    @TableField("exam_part")
    private String examPart;

    /** 检查医生ID */
    @TableField("exam_doctor_id")
    private String examDoctorId;

    /** 检查医生姓名 */
    @TableField("exam_doctor")
    private String examDoctor;

    /** 检查时间 */
    @TableField("exam_time")
    private LocalDateTime examTime;

    /** DR结果描述 */
    @TableField("dr_result")
    private String drResult;

    /** DR结论：NORMAL-正常，ABNORMAL-异常，RECHECK-需复查 */
    @TableField("conclusion")
    private String conclusion;

    /** 影像文件路径（DICOM或JPEG） */
    @TableField("image_path")
    private String imagePath;

    /** 报告PDF路径 */
    @TableField("report_path")
    private String reportPath;

    /**
     * 状态：
     * 0-待检查（条码已生成，居民未到）
     * 1-检查中
     * 2-已完成
     * 3-已上传县域
     * 4-已取消
     */
    private Integer status;

    /** 扫码操作员（院内扫码人员） */
    @TableField("scan_operator")
    private String scanOperator;

    /** 扫码时间 */
    @TableField("scan_time")
    private LocalDateTime scanTime;

    /** 同步县域时间 */
    @TableField("sync_time")
    private LocalDateTime syncTime;

    /** 备注 */
    private String remark;

    @TableField(value = "create_time", fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(value = "update_time", fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    @TableField("deleted")
    private Integer deleted;
}
