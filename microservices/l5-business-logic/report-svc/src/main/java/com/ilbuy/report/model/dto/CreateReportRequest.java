package com.ilbuy.report.model.dto;

import com.ilbuy.report.model.enums.ReportType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.Map;

@Data
public class CreateReportRequest {

    @NotNull(message = "报告类型不能为空")
    private ReportType type;

    @NotBlank(message = "报告标题不能为空")
    private String title;

    private Map<String, Object> parameters;
}
