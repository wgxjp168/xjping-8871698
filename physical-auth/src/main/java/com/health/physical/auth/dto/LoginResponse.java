package com.health.physical.auth.dto;

import lombok.Builder;
import lombok.Data;

import java.util.List;

/**
 * 登录响应DTO
 */
@Data
@Builder
public class LoginResponse {

    /** JWT Token */
    private String token;

    /** Token有效期（秒） */
    private Long expireIn;

    /** 医生ID */
    private String docId;

    /** 用户名 */
    private String username;

    /** 姓名 */
    private String name;

    /** 科室编码 */
    private String dept;

    /** 科室名称 */
    private String deptName;

    /** 职称 */
    private String title;

    /** 拥有权限的项目列表 */
    private List<String> projectCodes;

    /** 权限列表（projectCode:operateType 格式） */
    private List<String> permissions;
}
