package com.health.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 检查项目
 */
@Data
@TableName("check_item")
public class CheckItem {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String name;

    private String code;

    private String category;

    private String unit;

    private BigDecimal normalMin;

    private BigDecimal normalMax;

    private String normalText;

    private String deviceType;

    private Integer sort;

    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
