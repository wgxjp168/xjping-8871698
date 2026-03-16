package com.ilbuy.reportgen.model.dto;

import com.ilbuy.reportgen.model.enums.ClientType;
import com.ilbuy.reportgen.model.enums.ReportBusinessType;
import lombok.Builder;
import lombok.Data;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

/**
 * Internal report DTO passed from generator → format-output-svc.
 */
@Data
@Builder
public class GeneratedReport {
    private String jobNo;
    private String l5ReportNo;
    private Long userId;
    private String title;
    private ClientType clientType;
    private ReportBusinessType businessType;
    private Long brandId;
    private Long categoryId;
    private List<ReportSectionData> sections;
    private Map<String, Object> metadata;
    private OffsetDateTime generatedAt;

    // Format targets
    private boolean generateHtml;
    private boolean generatePdf;
    private boolean generateExcel;

    // Delivery targets
    private boolean deliverEmail;
    private String emailAddress;
    private boolean deliverWechat;
    private String wechatOpenId;
    private boolean deliverApp;
    private String appDeviceToken;
}
