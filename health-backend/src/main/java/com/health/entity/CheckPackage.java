package com.health.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 检查套餐
 */
@Data
@TableName("check_package")
public class CheckPackage {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String name;

    private String code;

    private String category;

    private BigDecimal price;

    private String description;

    private String imageUrl;

    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
