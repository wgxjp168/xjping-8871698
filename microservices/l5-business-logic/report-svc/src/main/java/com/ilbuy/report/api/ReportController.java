package com.ilbuy.report.api;

import com.ilbuy.report.model.dto.CreateReportRequest;
import com.ilbuy.report.model.dto.PageResult;
import com.ilbuy.report.model.dto.ReportDTO;
import com.ilbuy.report.model.enums.ReportStatus;
import com.ilbuy.report.model.enums.ReportType;
import com.ilbuy.report.service.ReportService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/reports")
@RequiredArgsConstructor
@Slf4j
public class ReportController {

    private final ReportService reportService;

    /**
     * POST /api/v1/reports – request report generation (async, returns PENDING report)
     */
    @PostMapping
    public ResponseEntity<ReportDTO> createReport(@Valid @RequestBody CreateReportRequest request,
                                                   Authentication authentication) {
        Long userId = (Long) authentication.getPrincipal();
        ReportDTO report = reportService.createReport(userId, request);
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(report);
    }

    /**
     * GET /api/v1/reports – list current user's reports (paginated, filter by type/status)
     */
    @GetMapping
    public ResponseEntity<PageResult<ReportDTO>> listReports(
            @RequestParam(required = false) ReportType type,
            @RequestParam(required = false) ReportStatus status,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            Authentication authentication) {
        Long userId = (Long) authentication.getPrincipal();
        PageResult<ReportDTO> result = reportService.listReports(userId, type, status, page, size);
        return ResponseEntity.ok(result);
    }

    /**
     * GET /api/v1/reports/{reportNo} – get report detail + status
     */
    @GetMapping("/{reportNo}")
    public ResponseEntity<ReportDTO> getReport(@PathVariable String reportNo,
                                                Authentication authentication) {
        Long userId = (Long) authentication.getPrincipal();
        ReportDTO report = reportService.getReport(userId, reportNo);
        return ResponseEntity.ok(report);
    }

    /**
     * GET /api/v1/reports/{reportNo}/download – get download URL (only if READY, log access)
     */
    @GetMapping("/{reportNo}/download")
    public ResponseEntity<Map<String, String>> getDownloadUrl(@PathVariable String reportNo,
                                                               Authentication authentication,
                                                               HttpServletRequest servletRequest) {
        Long userId = (Long) authentication.getPrincipal();
        String ipAddress = resolveClientIp(servletRequest);
        String url = reportService.getDownloadUrl(userId, reportNo, ipAddress);
        return ResponseEntity.ok(Map.of("downloadUrl", url));
    }

    /**
     * DELETE /api/v1/reports/{reportNo} – soft-delete (only owner can delete)
     */
    @DeleteMapping("/{reportNo}")
    public ResponseEntity<Void> deleteReport(@PathVariable String reportNo,
                                              Authentication authentication) {
        Long userId = (Long) authentication.getPrincipal();
        reportService.deleteReport(userId, reportNo);
        return ResponseEntity.noContent().build();
    }

    private String resolveClientIp(HttpServletRequest request) {
        String xForwardedFor = request.getHeader("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isBlank()) {
            return xForwardedFor.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}
