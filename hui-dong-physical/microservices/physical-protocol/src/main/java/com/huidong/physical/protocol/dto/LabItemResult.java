package com.huidong.physical.protocol.dto;

import lombok.Data;

/**
 * 单个检验项目结果
 */
@Data
public class LabItemResult {

    /** 项目代码（LOINC码） */
    private String itemCode;

    /** 项目名称 */
    private String itemName;

    /** 结果值 */
    private String resultValue;

    /** 单位 */
    private String unit;

    /** 参考范围 */
    private String referenceRange;

    /** 结果标志 N=正常 H=偏高 L=偏低 */
    private String resultFlag;

    /** 检验时间 */
    private String observationDateTime;
}
