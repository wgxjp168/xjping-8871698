package com.ilbuy.report.service;

import com.ilbuy.report.model.dto.CreateReportRequest;
import com.ilbuy.report.model.dto.PageResult;
import com.ilbuy.report.model.dto.ReportDTO;
import com.ilbuy.report.model.entity.Report;
import com.ilbuy.report.model.entity.ReportAccessLog;
import com.ilbuy.report.model.enums.ReportStatus;
import com.ilbuy.report.model.enums.ReportType;
import com.ilbuy.report.mq.ReportEventPublisher;
import com.ilbuy.report.repository.ReportAccessLogRepository;
import com.ilbuy.report.repository.ReportRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class ReportService {

    private final ReportRepository reportRepository;
    private final ReportAccessLogRepository reportAccessLogRepository;
    private final ReportEventPublisher reportEventPublisher;

    /**
     * Request async report generation. Returns a PENDING report immediately.
     */
    @Transactional
    public ReportDTO createReport(Long userId, CreateReportRequest request) {
        String reportNo = "RPT-" + UUID.randomUUID().toString().replace("-", "").substring(0, 16).toUpperCase();

        Report report = Report.builder()
            .reportNo(reportNo)
            .userId(userId)
            .title(request.getTitle())
            .type(request.getType())
            .status(ReportStatus.PENDING)
            .deleted(false)
            .build();

        report = reportRepository.save(report);
        log.info("Created report {} for userId={}, type={}", reportNo, userId, request.getType());

        // Publish async generation event
        reportEventPublisher.publishReportGenerateEvent(reportNo, userId);

        return toDTO(report);
    }

    /**
     * List current user's reports with optional type/status filter.
     */
    @Transactional(readOnly = true)
    public PageResult<ReportDTO> listReports(Long userId, ReportType type, ReportStatus status,
                                             int page, int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<Report> reportPage;

        if (type != null && status != null) {
            reportPage = reportRepository.findByUserIdAndTypeAndStatusAndDeletedFalse(userId, type, status, pageable);
        } else if (type != null) {
            reportPage = reportRepository.findByUserIdAndTypeAndDeletedFalse(userId, type, pageable);
        } else if (status != null) {
            reportPage = reportRepository.findByUserIdAndStatusAndDeletedFalse(userId, status, pageable);
        } else {
            reportPage = reportRepository.findByUserIdAndDeletedFalse(userId, pageable);
        }

        return PageResult.<ReportDTO>builder()
            .content(reportPage.getContent().stream().map(this::toDTO).toList())
            .page(reportPage.getNumber())
            .size(reportPage.getSize())
            .totalElements(reportPage.getTotalElements())
            .totalPages(reportPage.getTotalPages())
            .first(reportPage.isFirst())
            .last(reportPage.isLast())
            .build();
    }

    /**
     * Get report detail by reportNo. Must belong to the current user.
     */
    @Transactional(readOnly = true)
    public ReportDTO getReport(Long userId, String reportNo) {
        Report report = findReportByNo(reportNo);
        checkOwner(report, userId);
        return toDTO(report);
    }

    /**
     * Get download URL for a READY report. Logs the access and verifies ownership.
     */
    @Transactional
    public String getDownloadUrl(Long userId, String reportNo, String ipAddress) {
        Report report = findReportByNo(reportNo);
        checkOwner(report, userId);

        if (report.getStatus() != ReportStatus.READY) {
            throw new IllegalStateException("报告尚未就绪，当前状态: " + report.getStatus());
        }

        if (report.getExpiresAt() != null && report.getExpiresAt().isBefore(LocalDateTime.now())) {
            throw new IllegalStateException("报告已过期");
        }

        // Log the access
        ReportAccessLog accessLog = ReportAccessLog.builder()
            .reportId(report.getId())
            .userId(userId)
            .accessedAt(LocalDateTime.now())
            .ipAddress(ipAddress)
            .build();
        reportAccessLogRepository.save(accessLog);

        log.info("User {} downloaded report {} from ip={}", userId, reportNo, ipAddress);
        return report.getFileUrl();
    }

    /**
     * Soft-delete a report. Only the owner can delete it.
     */
    @Transactional
    public void deleteReport(Long userId, String reportNo) {
        Report report = findReportByNo(reportNo);
        checkOwner(report, userId);

        report.setDeleted(true);
        reportRepository.save(report);
        log.info("User {} soft-deleted report {}", userId, reportNo);
    }

    // ---- helpers ----

    private Report findReportByNo(String reportNo) {
        return reportRepository.findByReportNoAndDeletedFalse(reportNo)
            .orElseThrow(() -> new IllegalArgumentException("报告不存在: " + reportNo));
    }

    private void checkOwner(Report report, Long userId) {
        if (!report.getUserId().equals(userId)) {
            throw new IllegalArgumentException("无权访问该报告");
        }
    }

    private ReportDTO toDTO(Report report) {
        return ReportDTO.builder()
            .id(report.getId())
            .reportNo(report.getReportNo())
            .userId(report.getUserId())
            .title(report.getTitle())
            .type(report.getType())
            .status(report.getStatus())
            .fileUrl(report.getStatus() == ReportStatus.READY ? report.getFileUrl() : null)
            .fileSize(report.getFileSize())
            .expiresAt(report.getExpiresAt())
            .createdAt(report.getCreatedAt())
            .updatedAt(report.getUpdatedAt())
            .build();
    }
}
