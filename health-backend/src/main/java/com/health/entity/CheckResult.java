package com.health.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

/**
 * 体检结果明细
 */
@Data
@TableName("check_result")
public class CheckResult {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long orderId;

    private Long itemId;

    private String itemName;

    private String value;

    private String unit;

    private String normalRange;

    /** 标记: NORMAL/HIGH/LOW/ABNORMAL */
    private String flag;

    private Long deviceId;

    /** 数据来源: MANUAL/DEVICE */
    private String dataSource;

    private Long doctorId;

    private String remark;

    private LocalDateTime checkTime;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
