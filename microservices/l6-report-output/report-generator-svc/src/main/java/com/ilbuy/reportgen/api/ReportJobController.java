package com.ilbuy.reportgen.api;

import com.ilbuy.reportgen.model.dto.JobStatusDTO;
import com.ilbuy.reportgen.service.ReportGeneratorService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * Internal API for L6 report-generator-svc.
 * Primary ingress is via MQ; this REST API is for health checks and job status.
 */
@RestController
@RequestMapping("/internal/v1/generator-jobs")
@RequiredArgsConstructor
@Slf4j
public class ReportJobController {

    private final ReportGeneratorService generatorService;

    /**
     * GET /internal/v1/generator-jobs/{jobNo} – check generation job status
     */
    @GetMapping("/{jobNo}")
    public ResponseEntity<JobStatusDTO> getJobStatus(@PathVariable String jobNo) {
        JobStatusDTO dto = generatorService.getJobStatus(jobNo);
        return ResponseEntity.ok(dto);
    }

    /**
     * GET /internal/v1/generator-jobs/health – liveness probe
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of("status", "UP", "service", "report-generator-svc"));
    }

    // ---- L7 / L8 hook stubs (pre-reserved interfaces) ----

    /**
     * POST /internal/v1/generator-jobs/{jobNo}/monetize-hook
     * Reserved for L7 (Commercial Monetization Layer) – triggers premium upsell after report delivery.
     */
    @PostMapping("/{jobNo}/monetize-hook")
    public ResponseEntity<Map<String, String>> monetizeHook(@PathVariable String jobNo,
                                                             @RequestBody Map<String, Object> payload) {
        log.info("[L7 Hook] Monetize hook triggered for jobNo={}, payload={}", jobNo, payload);
        // TODO: implement L7 commercial monetization integration
        return ResponseEntity.accepted().body(Map.of("status", "RECEIVED", "jobNo", jobNo));
    }

    /**
     * POST /internal/v1/generator-jobs/{jobNo}/feedback-hook
     * Reserved for L8 (Feedback & Optimization Layer) – receives quality feedback for model improvement.
     */
    @PostMapping("/{jobNo}/feedback-hook")
    public ResponseEntity<Map<String, String>> feedbackHook(@PathVariable String jobNo,
                                                             @RequestBody Map<String, Object> feedback) {
        log.info("[L8 Hook] Feedback hook triggered for jobNo={}, feedback={}", jobNo, feedback);
        // TODO: implement L8 feedback & optimization pipeline integration
        return ResponseEntity.accepted().body(Map.of("status", "RECEIVED", "jobNo", jobNo));
    }
}
