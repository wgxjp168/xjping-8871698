package com.ilbuy.auth.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 用户凭证实体（认证专用表，只存储用于认证的数据）
 *
 * <p>用户业务信息由 L5 user-svc 维护，auth-svc 通过 userId 关联。
 */
@Data
@TableName("user_credential")
public class UserCredential {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 关联 user-svc 的用户 ID */
    @TableField("user_id")
    private Long userId;

    /** 登录用户名（唯一）*/
    @TableField("username")
    private String username;

    /** 手机号（唯一，可作为登录名）*/
    @TableField("phone")
    private String phone;

    /** 邮箱（唯一，可作为登录名）*/
    @TableField("email")
    private String email;

    /** BCrypt 密码哈希 */
    @TableField("password_hash")
    private String passwordHash;

    /**
     * 用户类型
     * <ul>
     *   <li>BUSINESS - B端企业用户（限流 1000次/分/IP）</li>
     *   <li>CONSUMER  - C端普通用户（限流 100次/分/用户）</li>
     * </ul>
     */
    @TableField("user_type")
    private String userType;

    /** 角色（逗号分隔）*/
    @TableField("roles")
    private String roles;

    /** 账号状态（1=启用，0=禁用）*/
    @TableField("enabled")
    private Integer enabled;

    @TableField(value = "created_at", fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(value = "updated_at", fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}
