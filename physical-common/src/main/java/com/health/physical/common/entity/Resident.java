package com.health.physical.common.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 居民信息表
 */
@Data
@TableName("physical_resident")
public class Resident implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 居民身份证号 */
    @TableField("id_card")
    private String idCard;

    /** 居民姓名 */
    private String name;

    /** 性别：1-男，2-女 */
    private Integer gender;

    /** 出生日期 */
    private LocalDate birthDate;

    /** 手机号 */
    private String phone;

    /** 地址 */
    private String address;

    /** 所属村/社区 */
    private String village;

    /** 所属乡镇 */
    private String town;

    /** 县域居民ID（县级系统ID） */
    @TableField("county_resident_id")
    private String countyResidentId;

    /** 状态：1-正常，0-禁用 */
    @TableField("status")
    private Integer status;

    @TableField(value = "create_time", fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(value = "update_time", fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    @TableField("deleted")
    private Integer deleted;
}
