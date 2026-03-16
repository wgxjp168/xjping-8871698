package com.ilbuy.format.api;

import com.ilbuy.format.model.dto.FormatJobRequest;
import com.ilbuy.format.model.dto.FormatJobResponse;
import com.ilbuy.format.model.enums.FormatType;
import com.ilbuy.format.service.FormatOutputService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * Internal REST API for format-output-svc.
 * Consumed by report-generator-svc (submit) and web portal / mobile clients (download).
 */
@RestController
@RequestMapping("/internal/v1/format-jobs")
@RequiredArgsConstructor
@Slf4j
public class FormatJobController {

    private final FormatOutputService formatOutputService;

    /**
     * POST /internal/v1/format-jobs
     * Submit a GeneratedReport for multi-format rendering.
     * Returns 202 ACCEPTED immediately; rendering is async.
     */
    @PostMapping
    public ResponseEntity<Map<String, Object>> submitFormatJob(@Valid @RequestBody FormatJobRequest request) {
        log.info("[FormatAPI] Format job request: jobNo={}, formats: html={} pdf={} excel={}",
                request.getJobNo(), request.isGenerateHtml(), request.isGeneratePdf(), request.isGenerateExcel());
        FormatJobResponse response = formatOutputService.submitFormatJob(request);
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(Map.of(
                "formatJobId", response.getFormatJobId(),
                "formatJobNo", response.getFormatJobNo(),
                "status",      response.getStatus()
        ));
    }

    /**
     * GET /internal/v1/format-jobs/{formatJobNo}
     * Poll format job status and retrieve file URLs once COMPLETED.
     */
    @GetMapping("/{formatJobNo}")
    public ResponseEntity<FormatJobResponse> getJobStatus(@PathVariable String formatJobNo) {
        return ResponseEntity.ok(formatOutputService.getJobStatusByNo(formatJobNo));
    }

    /**
     * GET /internal/v1/format-jobs/{formatJobNo}/download/{format}
     * Download a specific report format. Records access log.
     * format: HTML | PDF | EXCEL
     *
     * Query param: userId (for access control in internal cluster calls)
     */
    @GetMapping("/{formatJobNo}/download/{format}")
    public ResponseEntity<Map<String, Object>> downloadReport(
            @PathVariable String formatJobNo,
            @PathVariable String format,
            @RequestParam Long userId,
            HttpServletRequest request) {

        FormatType formatType;
        try {
            formatType = FormatType.valueOf(format.toUpperCase());
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of(
                    "error", "Invalid format. Supported: HTML, PDF, EXCEL"
            ));
        }

        String ipAddress  = resolveClientIp(request);
        String userAgent  = request.getHeader("User-Agent");

        String downloadUrl = formatOutputService.recordAccessAndGetUrl(
                formatJobNo, userId, formatType, ipAddress, userAgent
        );

        if (downloadUrl == null) {
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                    .body(Map.of("error", "File URL not available yet"));
        }

        return ResponseEntity.ok(Map.of(
                "formatJobNo", formatJobNo,
                "format",      formatType,
                "downloadUrl", downloadUrl
        ));
    }

    /**
     * GET /internal/v1/format-jobs/by-report/{l5ReportNo}/json
     * Enterprise API JSON output: returns full report metadata and file URLs as structured JSON.
     * No file download required – suitable for B2B system integration.
     */
    @GetMapping("/by-report/{l5ReportNo}/json")
    public ResponseEntity<FormatJobResponse> getJsonOutput(@PathVariable String l5ReportNo) {
        return ResponseEntity.ok(formatOutputService.getJsonOutput(l5ReportNo));
    }

    /**
     * GET /internal/v1/format-jobs/health
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of("status", "UP", "service", "format-output-svc"));
    }

    // ── L7 Pre-reserved: Commercial Monetization Layer ──

    /**
     * POST /internal/v1/format-jobs/{formatJobNo}/monetize-hook
     * L7 商业变现层预留接口 – 控制水印、分级访问、付费解锁等
     */
    @PostMapping("/{formatJobNo}/monetize-hook")
    public ResponseEntity<Map<String, String>> monetizeHook(@PathVariable String formatJobNo,
                                                             @RequestBody Map<String, Object> payload) {
        log.info("[L7 Hook] Monetize hook: formatJobNo={}, plan={}", formatJobNo, payload.get("plan"));
        // TODO: apply watermark for free tier, unlock full report for premium, trigger upsell flow
        return ResponseEntity.accepted().body(Map.of("status", "RECEIVED", "formatJobNo", formatJobNo));
    }

    // ── L8 Pre-reserved: Feedback & Optimization Layer ──

    /**
     * POST /internal/v1/format-jobs/{formatJobNo}/feedback-hook
     * L8 反馈优化层预留接口 – 收集报告质量评分，回传模型优化管道
     */
    @PostMapping("/{formatJobNo}/feedback-hook")
    public ResponseEntity<Map<String, String>> feedbackHook(@PathVariable String formatJobNo,
                                                             @RequestBody Map<String, Object> feedback) {
        log.info("[L8 Hook] Feedback hook: formatJobNo={}, rating={}, comment={}",
                formatJobNo, feedback.get("rating"), feedback.get("comment"));
        // TODO: forward to L8 ML feedback pipeline for model retraining
        return ResponseEntity.accepted().body(Map.of("status", "RECEIVED", "formatJobNo", formatJobNo));
    }

    private String resolveClientIp(HttpServletRequest request) {
        String xff = request.getHeader("X-Forwarded-For");
        if (xff != null && !xff.isBlank()) return xff.split(",")[0].trim();
        return request.getRemoteAddr();
    }
}
