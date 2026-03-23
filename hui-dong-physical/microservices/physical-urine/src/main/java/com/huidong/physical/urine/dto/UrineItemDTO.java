package com.huidong.physical.urine.dto;

import lombok.Data;

/**
 * 尿常规单项检验结果
 */
@Data
public class UrineItemDTO {

    /** 项目代码（如: URO=尿胆原, BLD=潜血, PRO=蛋白质等） */
    private String itemCode;

    /** 项目名称 */
    private String itemName;

    /** 结果值 */
    private String resultValue;

    /** 单位 */
    private String unit;

    /** 参考范围 */
    private String referenceRange;

    /** 结果标志 N=正常 P=阳性 +-=弱阳性 */
    private String resultFlag;
}
