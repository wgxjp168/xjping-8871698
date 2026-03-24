package com.health.dto;

import lombok.Data;

/**
 * 诊断查询条件
 */
@Data
public class DiagnosisQueryDTO {

    private Long orderId;
    private Long patientId;
    private Long doctorId;
    private String riskLevel;
    private String status;
    private Integer pageNum = 1;
    private Integer pageSize = 10;
}
