package com.health.vo;

import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 体检单视图对象
 */
@Data
public class CheckOrderVO {

    private Long id;
    private String orderNo;
    private Long patientId;
    private String patientName;
    private String patientPhone;
    private Integer patientGender;
    private Long packageId;
    private String packageName;
    private LocalDate checkDate;
    private Long doctorId;
    private String doctorName;
    private String status;
    private String statusName;
    private Integer totalScore;
    private String summary;
    private LocalDateTime createTime;
    private List<CheckResultVO> results;
}
