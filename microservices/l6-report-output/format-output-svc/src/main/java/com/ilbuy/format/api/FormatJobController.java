package com.ilbuy.format.api;

import com.ilbuy.format.model.dto.FormatJobRequest;
import com.ilbuy.format.model.dto.FormatJobResponse;
import com.ilbuy.format.service.FormatOutputService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * Internal REST API for format-output-svc.
 * Primary consumer: report-generator-svc.
 */
@RestController
@RequestMapping("/internal/v1/format-jobs")
@RequiredArgsConstructor
@Slf4j
public class FormatJobController {

    private final FormatOutputService formatOutputService;

    /**
     * POST /internal/v1/format-jobs
     * Accepts a GeneratedReport and kicks off async multi-format rendering.
     */
    @PostMapping
    public ResponseEntity<Map<String, Object>> submitFormatJob(@Valid @RequestBody FormatJobRequest request) {
        log.info("[FormatAPI] Received format job request for jobNo={}", request.getJobNo());
        FormatJobResponse response = formatOutputService.submitFormatJob(request);
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(Map.of(
                "formatJobId", response.getFormatJobId(),
                "formatJobNo", response.getFormatJobNo(),
                "status", response.getStatus()
        ));
    }

    /**
     * GET /internal/v1/format-jobs/{formatJobNo}
     * Poll format job status and file URLs.
     */
    @GetMapping("/{formatJobNo}")
    public ResponseEntity<FormatJobResponse> getJobStatus(@PathVariable String formatJobNo) {
        return ResponseEntity.ok(formatOutputService.getJobStatusByNo(formatJobNo));
    }

    /**
     * GET /internal/v1/format-jobs/by-report/{l5ReportNo}/json
     * Get JSON output for a report (direct API access, no file download).
     */
    @GetMapping("/by-report/{l5ReportNo}/json")
    public ResponseEntity<Object> getJsonOutput(@PathVariable String l5ReportNo) {
        return ResponseEntity.ok(formatOutputService.getJsonOutput(l5ReportNo));
    }

    /**
     * GET /internal/v1/format-jobs/health
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of("status", "UP", "service", "format-output-svc"));
    }

    // ---- L7 / L8 Pre-reserved interfaces ----

    /**
     * POST /internal/v1/format-jobs/{formatJobNo}/monetize-hook
     * L7 商业变现层接口预留
     */
    @PostMapping("/{formatJobNo}/monetize-hook")
    public ResponseEntity<Map<String, String>> monetizeHook(@PathVariable String formatJobNo,
                                                             @RequestBody Map<String, Object> payload) {
        log.info("[L7 Hook] Format monetize hook: formatJobNo={}", formatJobNo);
        // TODO: implement premium upsell, watermark for free tier, etc.
        return ResponseEntity.accepted().body(Map.of("status", "RECEIVED", "formatJobNo", formatJobNo));
    }

    /**
     * POST /internal/v1/format-jobs/{formatJobNo}/feedback-hook
     * L8 反馈优化层接口预留
     */
    @PostMapping("/{formatJobNo}/feedback-hook")
    public ResponseEntity<Map<String, String>> feedbackHook(@PathVariable String formatJobNo,
                                                             @RequestBody Map<String, Object> feedback) {
        log.info("[L8 Hook] Format feedback hook: formatJobNo={}, rating={}", formatJobNo, feedback.get("rating"));
        // TODO: forward to L8 model feedback pipeline
        return ResponseEntity.accepted().body(Map.of("status", "RECEIVED", "formatJobNo", formatJobNo));
    }
}
