package com.health.dto;

import lombok.Data;

/**
 * 体检单查询条件
 */
@Data
public class CheckOrderQueryDTO {

    private String orderNo;
    private Long patientId;
    private String patientName;
    private String status;
    private String checkDateStart;
    private String checkDateEnd;
    private Integer pageNum = 1;
    private Integer pageSize = 10;
}
