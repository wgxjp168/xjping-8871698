package com.ilbuy.format.model.dto;

import com.ilbuy.format.model.enums.FormatJobStatus;
import lombok.Builder;
import lombok.Data;

import java.time.OffsetDateTime;

@Data
@Builder
public class FormatJobResponse {
    private Long formatJobId;
    private String formatJobNo;
    private String l5ReportNo;
    private FormatJobStatus status;
    private String htmlUrl;
    private String pdfUrl;
    private String excelUrl;
    private OffsetDateTime expiresAt;
    private OffsetDateTime createdAt;
}
