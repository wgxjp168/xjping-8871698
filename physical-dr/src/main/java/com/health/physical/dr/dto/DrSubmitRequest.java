package com.health.physical.dr.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;

/**
 * DR检查结果提交请求DTO
 */
@Data
public class DrSubmitRequest {

    /** DR记录ID */
    @NotNull(message = "DR记录ID不能为空")
    private Long id;

    /** DR条码 */
    @NotBlank(message = "DR条码不能为空")
    private String drCode;

    /** 检查结果描述 */
    @NotBlank(message = "检查结果不能为空")
    private String drResult;

    /**
     * DR结论：NORMAL-正常，ABNORMAL-异常，RECHECK-需复查
     */
    @NotBlank(message = "检查结论不能为空")
    private String conclusion;

    /** 检查医生ID */
    @NotBlank(message = "检查医生不能为空")
    private String examDoctorId;

    /** 检查医生姓名 */
    private String examDoctor;

    /** 影像文件路径 */
    private String imagePath;

    /** 备注 */
    private String remark;
}
