package com.ilbuy.format.service;

import com.ilbuy.format.client.ChannelDeliveryClient;
import com.ilbuy.format.model.dto.FormatJobRequest;
import com.ilbuy.format.model.dto.FormatJobResponse;
import com.ilbuy.format.model.entity.FormatJob;
import com.ilbuy.format.model.enums.FormatJobStatus;
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
    private final HtmlFormatter htmlFormatter;
    private final PdfFormatter pdfFormatter;
    private final ExcelFormatter excelFormatter;
    private final MinioStorageService minioStorage;
    private final ChannelDeliveryClient channelDeliveryClient;

    /**
     * Create format job record and start async processing.
     */
    @Transactional
    public FormatJobResponse submitFormatJob(FormatJobRequest request) {
        // Idempotency: check if we already have a job for this generatorJobNo
        return jobRepository.findByGeneratorJobNo(request.getJobNo()).map(existingJob -> {
            log.warn("[FormatOutput] Duplicate request for generatorJobNo={}", request.getJobNo());
            return toResponse(existingJob);
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

            // Kick off async processing
            processAsync(job.getId(), request);

            return toResponse(job);
        });
    }

    @Async("formatOutputExecutor")
    public void processAsync(Long jobId, FormatJobRequest request) {
        FormatJob job = jobRepository.findById(jobId).orElseThrow();
        job.setStatus(FormatJobStatus.PROCESSING);
        job.setStartedAt(OffsetDateTime.now());
        jobRepository.save(job);

        try {
            String baseKey = request.getL5ReportNo() + "/" + request.getJobNo();

            String pdfUrl = null;
            String excelUrl = null;
            String htmlUrl = null;

            // Step 1: PDF
            if (request.isGeneratePdf()) {
                log.info("[FormatOutput] Generating PDF for {}", request.getJobNo());
                byte[] pdfBytes = pdfFormatter.format(request);
                pdfUrl = minioStorage.uploadPdf(baseKey + ".pdf", pdfBytes);
                job.setPdfUrl(pdfUrl);
                job.setPdfSize((long) pdfBytes.length);
            }

            // Step 2: Excel
            if (request.isGenerateExcel()) {
                log.info("[FormatOutput] Generating Excel for {}", request.getJobNo());
                byte[] excelBytes = excelFormatter.format(request);
                excelUrl = minioStorage.uploadExcel(baseKey + ".xlsx", excelBytes);
                job.setExcelUrl(excelUrl);
                job.setExcelSize((long) excelBytes.length);
            }

            // Step 3: HTML (with links to PDF/Excel)
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

            log.info("[FormatOutput] Job {} completed. HTML={}, PDF={}, Excel={}",
                    job.getFormatJobNo(), htmlUrl != null, pdfUrl != null, excelUrl != null);

            // Step 4: Trigger channel delivery
            channelDeliveryClient.triggerDelivery(job, request);

        } catch (Exception e) {
            log.error("[FormatOutput] Job {} failed: {}", job.getFormatJobNo(), e.getMessage(), e);
            job.setStatus(FormatJobStatus.FAILED);
            job.setErrorMessage(e.getMessage());
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
     * Generate JSON representation directly (no storage, inline response).
     */
    public Object getJsonOutput(String l5ReportNo) {
        FormatJob job = jobRepository.findAll().stream()
                .filter(j -> l5ReportNo.equals(j.getL5ReportNo()))
                .findFirst()
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
