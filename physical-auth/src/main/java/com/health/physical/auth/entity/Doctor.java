package com.health.physical.auth.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 医生账号表（从县域公卫系统同步）
 */
@Data
@TableName("physical_doctor")
public class Doctor implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 县域医生ID（唯一，用于同步） */
    @TableField("doc_id")
    private String docId;

    /** 登录用户名 */
    private String username;

    /** 密码（bcrypt加密，或对接SSO时可为空） */
    private String password;

    /** 姓名 */
    private String name;

    /** 手机号 */
    private String phone;

    /** 科室编码 */
    private String dept;

    /** 科室名称 */
    @TableField("dept_name")
    private String deptName;

    /** 职称 */
    private String title;

    /** 绑定MAC地址（网页端防越权，多个逗号分隔） */
    @TableField("mac_addresses")
    private String macAddresses;

    /** 最后登录时间 */
    @TableField("last_login_time")
    private LocalDateTime lastLoginTime;

    /** 最后登录IP */
    @TableField("last_login_ip")
    private String lastLoginIp;

    /** 状态：1-正常，0-禁用 */
    private Integer status;

    /** 是否从县域同步：1-是，0-否 */
    @TableField("county_synced")
    private Integer countySynced;

    @TableField(value = "create_time", fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(value = "update_time", fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    @TableField("deleted")
    private Integer deleted;
}
