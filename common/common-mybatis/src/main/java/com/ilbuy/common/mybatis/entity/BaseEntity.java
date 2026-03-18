package com.ilbuy.common.mybatis.entity;

import com.baomidou.mybatisplus.annotation.*;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serial;
import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 实体基类（所有业务表 DO 继承此类）
 *
 * <p>包含字段：
 * <ul>
 *   <li>id         — 主键（雪花算法自动生成）</li>
 *   <li>createTime — 创建时间（插入自动填充）</li>
 *   <li>updateTime — 更新时间（插入/更新自动填充）</li>
 *   <li>createBy   — 创建人 ID（插入自动填充）</li>
 *   <li>updateBy   — 修改人 ID（插入/更新自动填充）</li>
 *   <li>deleted    — 逻辑删除标记（0=未删除, 1=已删除）</li>
 *   <li>version    — 乐观锁版本号</li>
 * </ul>
 * </p>
 */
@Data
public abstract class BaseEntity implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    /** 主键（雪花算法） */
    @TableId(value = "id", type = IdType.ASSIGN_ID)
    @Schema(description = "主键 ID", accessMode = Schema.AccessMode.READ_ONLY)
    private Long id;

    /** 创建时间 */
    @TableField(value = "create_time", fill = FieldFill.INSERT)
    @Schema(description = "创建时间", accessMode = Schema.AccessMode.READ_ONLY)
    private LocalDateTime createTime;

    /** 最后修改时间 */
    @TableField(value = "update_time", fill = FieldFill.INSERT_UPDATE)
    @Schema(description = "更新时间", accessMode = Schema.AccessMode.READ_ONLY)
    private LocalDateTime updateTime;

    /** 创建人用户 ID */
    @TableField(value = "create_by", fill = FieldFill.INSERT)
    @Schema(description = "创建人 ID", accessMode = Schema.AccessMode.READ_ONLY)
    private Long createBy;

    /** 最后修改人用户 ID */
    @TableField(value = "update_by", fill = FieldFill.INSERT_UPDATE)
    @Schema(description = "更新人 ID", accessMode = Schema.AccessMode.READ_ONLY)
    private Long updateBy;

    /** 逻辑删除标记（0=未删除, 1=已删除） */
    @TableLogic
    @TableField(value = "deleted")
    @Schema(hidden = true)
    private Integer deleted;

    /** 乐观锁版本号 */
    @Version
    @TableField(value = "version")
    @Schema(description = "版本号（乐观锁）", accessMode = Schema.AccessMode.READ_ONLY)
    private Integer version;
}
