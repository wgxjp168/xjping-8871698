package com.ilbuy.reportgen.model.dto;

import com.ilbuy.reportgen.model.enums.ClientType;
import com.ilbuy.reportgen.model.enums.ReportBusinessType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * Message consumed from L5 REPORT_SVC → L6 generation queue.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReportGenerateEvent {

    private String l5ReportNo;
    private Long userId;
    private ClientType clientType;         // B2B | B2C_DEFINED | B2C_UNDEFINED
    private ReportBusinessType businessType;
    private Long brandId;
    private Long categoryId;
    private String title;
    private Map<String, Object> parameters;

    // Output format preferences (forwarded to format-output-svc)
    private boolean generateHtml;
    private boolean generatePdf;
    private boolean generateExcel;

    // Delivery channel preferences (forwarded to channel-delivery-svc)
    private boolean deliverEmail;
    private String emailAddress;
    private boolean deliverWechat;
    private String wechatOpenId;
    private boolean deliverApp;
    private String appDeviceToken;
}
