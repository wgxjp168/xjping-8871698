package com.ilbuy.report.model.dto;

import com.ilbuy.report.model.enums.ReportStatus;
import com.ilbuy.report.model.enums.ReportType;
import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class ReportDTO {

    private Long id;
    private String reportNo;
    private Long userId;
    private String title;
    private ReportType type;
    private ReportStatus status;
    private String fileUrl;
    private Long fileSize;
    private LocalDateTime expiresAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
