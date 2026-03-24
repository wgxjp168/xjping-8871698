package com.health.physical.auth.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;

/**
 * 权限校验请求DTO
 */
@Data
public class PermCheckRequest {

    /** 医生ID */
    @NotBlank(message = "医生ID不能为空")
    private String docId;

    /** 项目编码 */
    @NotBlank(message = "项目编码不能为空")
    private String projectCode;

    /** 操作类型：QUERY/INPUT/AUDIT */
    @NotBlank(message = "操作类型不能为空")
    private String operateType;
}
