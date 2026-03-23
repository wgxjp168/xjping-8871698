package com.huidong.physical.core.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.huidong.physical.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * 居民信息（缓存表）
 * 数据来源：从县域智慧公卫平台同步
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("t_resident")
public class Resident extends BaseEntity {

    /** 居民唯一标识（对应县域平台ID） */
    private String residentCode;

    /** 身份证号 */
    private String idCard;

    /** 姓名 */
    private String name;

    /** 性别 0=女 1=男 */
    private Integer gender;

    /** 出生日期 */
    private String birthDate;

    /** 手机号 */
    private String phone;

    /** 所属村/社区 */
    private String village;

    /** 所属乡镇 */
    private String town;

    /** 慢病标签（JSON） */
    private String chronicTags;

    /** 是否启用 */
    private Integer enabled;
}
