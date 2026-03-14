package com.ilbuy.common.mybatis.entity;

import com.baomidou.mybatisplus.annotation.*;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serial;
import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 所有实体类的基础父类
 *
 * <p>提供公共字段：
 * <ul>
 *   <li>id - 雪花算法主键（自动生成）</li>
 *   <li>createTime - 创建时间（自动填充）</li>
 *   <li>updateTime - 更新时间（自动填充）</li>
 *   <li>deleted - 逻辑删除标记</li>
 * </ul>
 *
 * <p>子类使用示例：
 * <pre>{@code
 * @TableName("ilbuy_user")
 * public class User extends BaseEntity {
 *     private String username;
 *     // ...
 * }
 * }</pre>
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@Data
public abstract class BaseEntity implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    /**
     * 主键ID（雪花算法，自动生成）
     */
    @Schema(description = "主键ID")
    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    /**
     * 创建时间（自动填充，插入时设置）
     */
    @Schema(description = "创建时间")
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    /**
     * 最后更新时间（自动填充，插入和更新时设置）
     */
    @Schema(description = "更新时间")
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    /**
     * 逻辑删除标记（0=未删除，1=已删除）
     * MyBatis-Plus自动处理，查询时自动过滤已删除数据
     */
    @Schema(description = "是否删除", hidden = true)
    @TableLogic(value = "0", delval = "1")
    private Integer deleted;
}
