package com.ilbuy.l5.user_svc.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 用户实体
 * 支持 B2B 企业用户 和 B2C 个人用户
 */
@Data
@TableName("ilbuy_user")
public class User {

    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    /** 用户名 */
    private String username;

    /** 加密密码 */
    private String password;

    /** 手机号 */
    private String phone;

    /** 邮箱 */
    private String email;

    /** 用户类型: B2B | B2C */
    private String userType;

    /** 企业名称（B2B用户） */
    private String companyName;

    /** 统一社会信用代码（B2B用户） */
    private String creditCode;

    /** 用户状态: 0-禁用 1-正常 */
    @TableField(value = "status")
    private Integer status;

    /** 会员等级: FREE | BASIC | PRO | ENTERPRISE */
    private String memberLevel;

    /** 会员到期时间 */
    private LocalDateTime memberExpireTime;

    /** 累计决策次数 */
    private Integer decisionCount;

    /** 创建时间 */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    /** 更新时间 */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    /** 逻辑删除 */
    @TableLogic
    private Integer deleted;
}
