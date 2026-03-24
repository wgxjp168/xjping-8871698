package com.health.physical.common.constant;

/**
 * 权限常量定义
 */
public interface PermissionConstants {

    /** 项目编码 - 生化 */
    String PROJECT_BIOCHEM = "BIOCHEM";

    /** 项目编码 - 血常规 */
    String PROJECT_CBC = "CBC";

    /** 项目编码 - 糖化血红蛋白 */
    String PROJECT_HBA1C = "HBA1C";

    /** 项目编码 - 尿常规 */
    String PROJECT_URINE = "URINE";

    /** 项目编码 - DR放射 */
    String PROJECT_DR = "DR";

    /** 项目编码 - 血压 */
    String PROJECT_BP = "BP";

    /** 项目编码 - 体重身高 */
    String PROJECT_BODY = "BODY";

    /** 操作类型 - 查询 */
    String OPERATE_QUERY = "QUERY";

    /** 操作类型 - 录入 */
    String OPERATE_INPUT = "INPUT";

    /** 操作类型 - 审核 */
    String OPERATE_AUDIT = "AUDIT";

    /** 科室 - 化验室 */
    String DEPT_LAB = "LAB";

    /** 科室 - DR室 */
    String DEPT_DR = "DR_ROOM";

    /** 科室 - 公卫科 */
    String DEPT_PUBLIC_HEALTH = "PUBLIC_HEALTH";

    /** JWT Token Header */
    String TOKEN_HEADER = "Authorization";

    /** JWT Token Prefix */
    String TOKEN_PREFIX = "Bearer ";

    /** Redis 权限缓存前缀 */
    String REDIS_PERM_PREFIX = "physical:perm:";

    /** Redis 用户信息缓存前缀 */
    String REDIS_USER_PREFIX = "physical:user:";

    /** Redis Token缓存前缀 */
    String REDIS_TOKEN_PREFIX = "physical:token:";

    /** Token有效期（秒） - 12小时 */
    int TOKEN_EXPIRE_SECONDS = 43200;
}
