package com.ilbuy.reportgen.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ilbuy.reportgen.model.dto.ReportGenerateEvent;
import com.ilbuy.reportgen.model.entity.ReportJob;
import com.ilbuy.reportgen.model.enums.ClientType;
import com.ilbuy.reportgen.model.enums.JobStatus;
import com.ilbuy.reportgen.model.enums.ReportBusinessType;
import com.ilbuy.reportgen.repository.ReportJobRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * Scheduled retry for FAILED report generation jobs.
 * Picks up jobs that failed (retryCount < maxRetries) and re-submits them.
 * Runs every 5 minutes. Max 3 retry attempts per job.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class RetryScheduler {

    private final ReportJobRepository jobRepository;
    private final ReportGeneratorService generatorService;
    private final ObjectMapper objectMapper;

    @Value("${report.generator.max-retries:3}")
    private int maxRetries;

    @Scheduled(fixedDelay = 5 * 60 * 1000, initialDelay = 60 * 1000)
    public void retryFailedJobs() {
        List<ReportJob> retryable = jobRepository.findPendingAndRetryableJobs();

        if (retryable.isEmpty()) {
            log.debug("[RetryScheduler] No retryable jobs found");
            return;
        }

        log.info("[RetryScheduler] Found {} retryable jobs", retryable.size());

        for (ReportJob job : retryable) {
            if (job.getRetryCount() >= maxRetries) {
                log.warn("[RetryScheduler] Job {} exceeded max retries ({}), marking FAILED permanently",
                        job.getJobNo(), maxRetries);
                job.setStatus(JobStatus.FAILED);
                job.setErrorMessage("Exceeded max retry attempts (" + maxRetries + ")");
                jobRepository.save(job);
                continue;
            }

            try {
                ReportGenerateEvent event = reconstructEvent(job);
                generatorService.retryJob(job, event);
                log.info("[RetryScheduler] Retrying job {} (attempt {})", job.getJobNo(), job.getRetryCount() + 1);
            } catch (Exception e) {
                log.error("[RetryScheduler] Failed to retry job {}: {}", job.getJobNo(), e.getMessage());
            }
        }
    }

    /**
     * Reconstruct a ReportGenerateEvent from the persisted ReportJob.
     * Parameters are stored as JSON in the job record.
     */
    private ReportGenerateEvent reconstructEvent(ReportJob job) {
        Map<String, Object> params = parseParameters(job.getParameters());

        return ReportGenerateEvent.builder()
                .l5ReportNo(job.getL5ReportNo())
                .userId(job.getUserId())
                .clientType(job.getClientType())
                .businessType(job.getBusinessType())
                .brandId(job.getBrandId())
                .categoryId(job.getCategoryId())
                .parameters(params)
                // Default to all formats on retry
                .generateHtml(true)
                .generatePdf(true)
                .generateExcel(true)
                .build();
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parseParameters(String json) {
        if (json == null || json.isBlank()) return Map.of();
        try {
            return objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {});
        } catch (Exception e) {
            log.warn("[RetryScheduler] Failed to parse parameters JSON: {}", e.getMessage());
            return Map.of();
        }
    }
}
