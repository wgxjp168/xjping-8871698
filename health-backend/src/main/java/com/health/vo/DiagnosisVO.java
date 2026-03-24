package com.health.vo;

import lombok.Data;
import java.time.LocalDateTime;

/**
 * 诊断报告视图对象
 */
@Data
public class DiagnosisVO {

    private Long id;
    private Long orderId;
    private String orderNo;
    private Long patientId;
    private String patientName;
    private Long doctorId;
    private String doctorName;
    private Integer healthScore;
    private String conclusion;
    private String suggestion;
    private String abnormalItems;
    private String riskLevel;
    private String riskLevelName;
    private String status;
    private String statusName;
    private LocalDateTime confirmTime;
    private LocalDateTime publishTime;
    private LocalDateTime createTime;
}
