package com.health.physical.dr.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;

/**
 * DR条码扫描请求DTO
 * 院内DR技师扫码时传入
 */
@Data
public class DrScanRequest {

    /** DR条码 */
    @NotBlank(message = "DR条码不能为空")
    private String drCode;

    /** 操作医生ID（从Token中解析，可选传入校验） */
    private String doctorId;
}
