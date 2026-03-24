package com.health.physical.auth.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 医生项目权限表
 */
@Data
@TableName("physical_doc_permission")
public class DocPermission implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 医生ID（县域系统同步） */
    @TableField("doc_id")
    private String docId;

    /** 医生姓名 */
    @TableField("doc_name")
    private String docName;

    /** 所属科室编码 */
    @TableField("dept")
    private String dept;

    /** 所属科室名称 */
    @TableField("dept_name")
    private String deptName;

    /**
     * 项目编码：BIOCHEM/CBC/HBA1C/URINE/DR/BP/BODY
     * 对应：生化/血常规/糖化血红蛋白/尿常规/DR放射/血压/体重身高
     */
    @TableField("project_code")
    private String projectCode;

    /** 项目名称 */
    @TableField("project_name")
    private String projectName;

    /**
     * 操作类型：QUERY-查询，INPUT-录入，AUDIT-审核
     */
    @TableField("operate_type")
    private String operateType;

    /** 权限范围：ALL-全院，OWN-本院，ZONE-指定片区 */
    @TableField("scope")
    private String scope;

    /** 指定片区（scope=ZONE时有效，逗号分隔） */
    @TableField("zone_codes")
    private String zoneCodes;

    /** 状态：1-有效，0-禁用 */
    private Integer status;

    /** 授权人 */
    @TableField("granted_by")
    private String grantedBy;

    @TableField(value = "create_time", fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(value = "update_time", fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
