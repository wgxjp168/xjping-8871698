package com.huidong.physical.urine.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 下乡尿常规数据上传请求
 */
@Data
public class UrineUploadDTO {

    /** 客户端生成的幂等上传ID（用于断点续传去重） */
    @NotBlank(message = "上传ID不能为空")
    private String uploadId;

    /** 居民身份证号或居民编码 */
    @NotBlank(message = "居民标识不能为空")
    private String residentIdentifier;

    /** 标识类型 1=居民编码 2=身份证号 */
    @NotNull(message = "标识类型不能为空")
    private Integer identifierType;

    /** 设备编码（优利特尿机） */
    @NotBlank(message = "设备编码不能为空")
    private String deviceCode;

    /** 采集时间 */
    @NotNull(message = "采集时间不能为空")
    private LocalDateTime collectTime;

    /** 尿常规检验项目列表 */
    @NotNull(message = "检验项目不能为空")
    private List<UrineItemDTO> items;

    /** 原始数据（设备输出原文，用于审计） */
    private String rawData;

    /** 网络类型（4G/5G/WIFI），用于记录 */
    private String networkType;
}
