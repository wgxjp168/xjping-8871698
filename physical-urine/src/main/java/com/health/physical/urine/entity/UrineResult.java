package com.health.physical.urine.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 尿常规检验结果
 */
@Data
@TableName("physical_urine_result")
public class UrineResult implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 关联体检记录ID */
    @TableField("physical_id")
    private Long physicalId;

    /** 居民ID */
    @TableField("resident_id")
    private Long residentId;

    /** 设备ID（优利特尿机SN） */
    @TableField("device_id")
    private String deviceId;

    /** 标本条码 */
    @TableField("barcode")
    private String barcode;

    // ===== 尿常规指标 =====
    /** 颜色 */
    private String color;

    /** 透明度 */
    private String clarity;

    /** 比重 */
    @TableField("specific_gravity")
    private String specificGravity;

    /** pH值 */
    private String ph;

    /** 白细胞 LEU */
    @TableField("leu")
    private String leu;

    /** 亚硝酸盐 NIT */
    @TableField("nit")
    private String nit;

    /** 尿蛋白 PRO */
    @TableField("pro")
    private String pro;

    /** 葡萄糖 GLU */
    @TableField("glu")
    private String glu;

    /** 酮体 KET */
    @TableField("ket")
    private String ket;

    /** 胆红素 BIL */
    @TableField("bil")
    private String bil;

    /** 尿胆原 URO */
    @TableField("uro")
    private String uro;

    /** 红细胞 ERY */
    @TableField("ery")
    private String ery;

    /** 隐血 BLD */
    @TableField("bld")
    private String bld;

    /** 维生素C VC */
    @TableField("vc")
    private String vc;

    /** 微白蛋白 mALB */
    @TableField("malb")
    private String malb;

    /** 原始JSON数据（来自设备） */
    @TableField("raw_data")
    private String rawData;

    /** 采集时间（下乡采集） */
    @TableField("collect_time")
    private LocalDateTime collectTime;

    /** 上传时间（4G上传） */
    @TableField("upload_time")
    private LocalDateTime uploadTime;

    /** 同步状态：0-未同步，1-已同步，2-同步失败 */
    @TableField("sync_status")
    private Integer syncStatus;

    /** 状态 */
    private Integer status;

    @TableField(value = "create_time", fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(value = "update_time", fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    @TableField("deleted")
    private Integer deleted;
}
