package com.ilbuy.format.service;

import com.ilbuy.format.client.ChannelDeliveryClient;
import com.ilbuy.format.model.dto.FormatJobRequest;
import com.ilbuy.format.model.dto.FormatJobResponse;
import com.ilbuy.format.model.entity.FormatAccessLog;
import com.ilbuy.format.model.entity.FormatJob;
import com.ilbuy.format.model.enums.FormatJobStatus;
import com.ilbuy.format.model.enums.FormatType;
import com.ilbuy.format.repository.FormatAccessLogRepository;
import com.ilbuy.format.repository.FormatJobRepository;
import com.ilbuy.format.service.formatter.ExcelFormatter;
import com.ilbuy.format.service.formatter.HtmlFormatter;
import com.ilbuy.format.service.formatter.PdfFormatter;
import com.ilbuy.format.storage.MinioStorageService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class FormatOutputService {

    private final FormatJobRepository jobRepository;
    private final FormatAccessLogRepository accessLogRepository;
    private final HtmlFormatter htmlFormatter;
    private final PdfFormatter pdfFormatter;
    private final ExcelFormatter excelFormatter;
    private final MinioStorageService minioStorage;
    private final ChannelDeliveryClient channelDeliveryClient;

    /**
     * Create format job record (synchronous + transactional) then kick off async rendering.
     * Idempotent: returns existing job if already submitted.
     */
    @Transactional
    public FormatJobResponse submitFormatJob(FormatJobRequest request) {
        return jobRepository.findByGeneratorJobNo(request.getJobNo()).map(existing -> {
            log.warn("[FormatOutput] Duplicate request for generatorJobNo={}", request.getJobNo());
            return toResponse(existing);
        }).orElseGet(() -> {
            String formatJobNo = "FMT-" + UUID.randomUUID().toString().replace("-", "").substring(0, 16).toUpperCase();
            FormatJob job = FormatJob.builder()
                    .formatJobNo(formatJobNo)
                    .generatorJobNo(request.getJobNo())
                    .l5ReportNo(request.getL5ReportNo())
                    .userId(request.getUserId())
                    .title(request.getTitle())
                    .clientType(request.getClientType())
                    .status(FormatJobStatus.PENDING)
                    .expiresAt(OffsetDateTime.now().plusHours(72))
                    .build();
            job = jobRepository.save(job);
            log.info("[FormatOutput] Created format job: {}", formatJobNo);

            // Kick off async rendering (separate thread, separate transaction)
            processAsync(job.getId(), request);

            return toResponse(job);
        });
    }

    /**
     * Async rendering pipeline: PDF → Excel → HTML → channel delivery.
     * Separate from the @Transactional submit to avoid long-held connections.
     */
    @Async("formatOutputExecutor")
    public void processAsync(Long jobId, FormatJobRequest request) {
        FormatJob job = jobRepository.findById(jobId).orElseThrow();
        job.setStatus(FormatJobStatus.PROCESSING);
        job.setStartedAt(OffsetDateTime.now());
        jobRepository.save(job);

        try {
            String baseKey = request.getL5ReportNo() + "/" + request.getJobNo();
            String pdfUrl = null, excelUrl = null, htmlUrl = null;

            // PDF (generate first so HTML can link to it)
            if (request.isGeneratePdf()) {
                log.info("[FormatOutput] Generating PDF for {}", request.getJobNo());
                byte[] pdfBytes = pdfFormatter.format(request);
                pdfUrl = minioStorage.uploadPdf(baseKey + ".pdf", pdfBytes);
                job.setPdfUrl(pdfUrl);
                job.setPdfSize((long) pdfBytes.length);
            }

            // Excel
            if (request.isGenerateExcel()) {
                log.info("[FormatOutput] Generating Excel for {}", request.getJobNo());
                byte[] excelBytes = excelFormatter.format(request);
                excelUrl = minioStorage.uploadExcel(baseKey + ".xlsx", excelBytes);
                job.setExcelUrl(excelUrl);
                job.setExcelSize((long) excelBytes.length);
            }

            // HTML (with embedded links to PDF + Excel)
            if (request.isGenerateHtml()) {
                log.info("[FormatOutput] Generating HTML for {}", request.getJobNo());
                byte[] htmlBytes = htmlFormatter.format(request, pdfUrl, excelUrl);
                htmlUrl = minioStorage.uploadHtml(baseKey + ".html", htmlBytes);
                job.setHtmlUrl(htmlUrl);
                job.setHtmlSize((long) htmlBytes.length);
            }

            job.setStatus(FormatJobStatus.COMPLETED);
            job.setCompletedAt(OffsetDateTime.now());
            jobRepository.save(job);

            log.info("[FormatOutput] Job {} completed. html={} pdf={} excel={}",
                    job.getFormatJobNo(), htmlUrl != null, pdfUrl != null, excelUrl != null);

            // Trigger multi-channel delivery
            channelDeliveryClient.triggerDelivery(job, request);

        } catch (Exception e) {
            log.error("[FormatOutput] Job {} failed: {}", job.getFormatJobNo(), e.getMessage(), e);
            job.setStatus(FormatJobStatus.FAILED);
            job.setErrorMessage(e.getMessage() != null ? e.getMessage().substring(0, Math.min(e.getMessage().length(), 500)) : "Unknown error");
            jobRepository.save(job);
        }
    }

    public FormatJobResponse getJobStatus(Long jobId) {
        FormatJob job = jobRepository.findById(jobId)
                .orElseThrow(() -> new RuntimeException("Format job not found: " + jobId));
        return toResponse(job);
    }

    public FormatJobResponse getJobStatusByNo(String formatJobNo) {
        FormatJob job = jobRepository.findByFormatJobNo(formatJobNo)
                .orElseThrow(() -> new RuntimeException("Format job not found: " + formatJobNo));
        return toResponse(job);
    }

    /**
     * Record a file access event (download/view) and return the pre-signed URL.
     * Used by the download endpoint for audit + analytics.
     */
    @Transactional
    public String recordAccessAndGetUrl(String formatJobNo, Long userId,
                                        FormatType formatType, String ipAddress, String userAgent) {
        FormatJob job = jobRepository.findByFormatJobNo(formatJobNo)
                .orElseThrow(() -> new RuntimeException("Format job not found: " + formatJobNo));

        if (job.getStatus() != FormatJobStatus.COMPLETED) {
            throw new RuntimeException("Report not ready yet. Status: " + job.getStatus());
        }
        if (OffsetDateTime.now().isAfter(job.getExpiresAt())) {
            throw new RuntimeException("Report has expired");
        }
        // Access control: only the owner can download
        if (!job.getUserId().equals(userId)) {
            throw new SecurityException("Access denied to format job " + formatJobNo);
        }

        // Log the access
        FormatAccessLog logEntry = FormatAccessLog.builder()
                .formatJob(job)
                .userId(userId)
                .format(formatType)
                .ipAddress(ipAddress)
                .userAgent(userAgent)
                .build();
        accessLogRepository.save(logEntry);

        return switch (formatType) {
            case HTML  -> job.getHtmlUrl();
            case PDF   -> job.getPdfUrl();
            case EXCEL -> job.getExcelUrl();
            default    -> throw new RuntimeException("Unsupported format type: " + formatType);
        };
    }

    /**
     * JSON API output: returns the full format job response as structured JSON.
     * For enterprise API integration – no file download required.
     */
    public FormatJobResponse getJsonOutput(String l5ReportNo) {
        FormatJob job = jobRepository.findByL5ReportNo(l5ReportNo)
                .orElseThrow(() -> new RuntimeException("No format job for report: " + l5ReportNo));
        return toResponse(job);
    }

    private FormatJobResponse toResponse(FormatJob job) {
        return FormatJobResponse.builder()
                .formatJobId(job.getId())
                .formatJobNo(job.getFormatJobNo())
                .l5ReportNo(job.getL5ReportNo())
                .status(job.getStatus())
                .htmlUrl(job.getHtmlUrl())
                .pdfUrl(job.getPdfUrl())
                .excelUrl(job.getExcelUrl())
                .expiresAt(job.getExpiresAt())
                .createdAt(job.getCreatedAt())
                .build();
    }
}
