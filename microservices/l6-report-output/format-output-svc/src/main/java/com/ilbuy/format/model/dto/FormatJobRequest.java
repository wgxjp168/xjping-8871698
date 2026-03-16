package com.ilbuy.format.model.dto;

import lombok.Data;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

/**
 * Incoming request from report-generator-svc.
 * Matches GeneratedReport DTO shape.
 */
@Data
public class FormatJobRequest {
    private String jobNo;               // generator jobNo
    private String l5ReportNo;
    private Long userId;
    private String title;
    private String clientType;
    private String businessType;
    private Long brandId;
    private Long categoryId;
    private List<SectionDTO> sections;
    private Map<String, Object> metadata;
    private OffsetDateTime generatedAt;

    // Format targets
    private boolean generateHtml;
    private boolean generatePdf;
    private boolean generateExcel;

    // Delivery targets (forwarded to channel-delivery-svc)
    private boolean deliverEmail;
    private String emailAddress;
    private boolean deliverWechat;
    private String wechatOpenId;
    private boolean deliverApp;
    private String appDeviceToken;
}
