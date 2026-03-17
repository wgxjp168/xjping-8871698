package com.ilbuy.bmonetize.dto;

import jakarta.validation.constraints.*;
import lombok.Data;

@Data
public class RecordApiUsageRequest {
    @NotNull private Long corpId;
    @NotBlank private String endpoint;
    private Long callCount = 1L;
    private String contractNo;
}
