package com.health.dto;

import lombok.Data;
import javax.validation.constraints.NotNull;

/**
 * 诊断保存请求
 */
@Data
public class DiagnosisSaveDTO {

    private Long id;

    @NotNull(message = "体检单ID不能为空")
    private Long orderId;

    private Integer healthScore;

    private String conclusion;

    private String suggestion;

    private String abnormalItems;

    private String riskLevel;
}
