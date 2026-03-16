package com.ilbuy.reportgen.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ilbuy.reportgen.client.FormatOutputClient;
import com.ilbuy.reportgen.model.dto.GeneratedReport;
import com.ilbuy.reportgen.model.dto.JobStatusDTO;
import com.ilbuy.reportgen.model.dto.ReportGenerateEvent;
import com.ilbuy.reportgen.model.dto.ReportSectionData;
import com.ilbuy.reportgen.model.entity.ReportJob;
import com.ilbuy.reportgen.model.entity.ReportSection;
import com.ilbuy.reportgen.model.enums.JobStatus;
import com.ilbuy.reportgen.repository.ReportJobRepository;
import com.ilbuy.reportgen.repository.ReportSectionRepository;
import com.ilbuy.reportgen.service.generator.ReportGeneratorStrategy;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class ReportGeneratorService {

    private final List<ReportGeneratorStrategy> strategies;
    private final ReportJobRepository jobRepository;
    private final ReportSectionRepository sectionRepository;
    private final FormatOutputClient formatOutputClient;
    private final ObjectMapper objectMapper;

    private Map<com.ilbuy.reportgen.model.enums.ClientType, ReportGeneratorStrategy> strategyMap;

    @PostConstruct
    public void initStrategyMap() {
        strategyMap = strategies.stream()
                .collect(Collectors.toMap(ReportGeneratorStrategy::supports, Function.identity()));
        log.info("Loaded {} report generator strategies: {}", strategyMap.size(), strategyMap.keySet());
    }

    /**
     * Step 1 (called by MQ consumer, runs on MQ thread):
     * Idempotency check + create PENDING job record synchronously, then kick off async processing.
     * Keeping DB write and async trigger separate avoids the @Async+@Transactional proxy pitfall.
     */
    @Transactional
    public ReportJob createJobRecord(ReportGenerateEvent event) {
        // Idempotency check
        return jobRepository.findByL5ReportNo(event.getL5ReportNo()).orElseGet(() -> {
            String jobNo = "RG-" + UUID.randomUUID().toString().replace("-", "").substring(0, 16).toUpperCase();
            ReportJob job = ReportJob.builder()
                    .jobNo(jobNo)
                    .l5ReportNo(event.getL5ReportNo())
                    .userId(event.getUserId())
                    .clientType(event.getClientType())
                    .businessType(event.getBusinessType())
                    .brandId(event.getBrandId())
                    .categoryId(event.getCategoryId())
                    .parameters(toJson(event.getParameters()))
                    .status(JobStatus.PENDING)
                    .build();
            return jobRepository.save(job);
        });
    }

    /**
     * Step 2 (called after createJobRecord, runs in dedicated thread pool):
     * The heavy report generation + section persistence + format submission.
     * No @Transactional here — each DB operation uses its own connection to avoid long-held transactions.
     */
    @Async("reportGeneratorExecutor")
    public void processJobAsync(ReportJob job, ReportGenerateEvent event) {
        if (job.getStatus() == JobStatus.COMPLETED) {
            log.warn("[Generator] Job {} already completed, skipping", job.getJobNo());
            return;
        }

        // Mark as PROCESSING
        job.setStatus(JobStatus.PROCESSING);
        job.setStartedAt(OffsetDateTime.now());
        jobRepository.save(job);

        try {
            ReportGeneratorStrategy strategy = strategyMap.get(event.getClientType());
            if (strategy == null) {
                throw new IllegalArgumentException("No generator strategy for clientType=" + event.getClientType());
            }

            GeneratedReport generated = strategy.generate(event);
            // Attach the jobNo so downstream services can correlate
            generated.setJobNo(job.getJobNo());

            // Persist sections (each save is its own short transaction)
            saveSections(job, generated.getSections());

            // Forward to format-output-svc
            Long formatJobId = formatOutputClient.submitFormatJob(generated);

            // Mark complete
            job.setStatus(JobStatus.COMPLETED);
            job.setResultJson(toJson(Map.of("sectionCount", generated.getSections().size())));
            job.setFormatJobId(formatJobId);
            job.setCompletedAt(OffsetDateTime.now());
            jobRepository.save(job);

            log.info("[Generator] Job {} COMPLETED, formatJobId={}", job.getJobNo(), formatJobId);

        } catch (Exception e) {
            log.error("[Generator] Job {} FAILED: {}", job.getJobNo(), e.getMessage(), e);
            job.setStatus(JobStatus.FAILED);
            job.setErrorMessage(truncate(e.getMessage(), 500));
            job.setRetryCount(job.getRetryCount() + 1);
            jobRepository.save(job);
        }
    }

    /**
     * Retry scheduler entry point – called by RetryScheduler for FAILED jobs.
     */
    public void retryJob(ReportJob job, ReportGenerateEvent event) {
        log.info("[Generator] Retrying job {} (attempt {})", job.getJobNo(), job.getRetryCount() + 1);
        job.setStatus(JobStatus.RETRYING);
        jobRepository.save(job);
        processJobAsync(job, event);
    }

    @Transactional
    public void saveSections(ReportJob job, List<ReportSectionData> sections) {
        // Clean previous sections if retrying
        sectionRepository.deleteByJobId(job.getId());

        List<ReportSection> entities = sections.stream().map(s -> ReportSection.builder()
                .job(job)
                .sectionKey(s.getSectionKey())
                .title(s.getTitle())
                .content(toJson(s.getContent()))
                .charts(toJson(s.getCharts()))
                .orderIndex(s.getOrderIndex())
                .build()).collect(Collectors.toList());
        sectionRepository.saveAll(entities);
    }

    public JobStatusDTO getJobStatus(String jobNo) {
        ReportJob job = jobRepository.findByJobNo(jobNo)
                .orElseThrow(() -> new RuntimeException("Job not found: " + jobNo));
        return toDTO(job);
    }

    public List<JobStatusDTO> listJobsByUser(Long userId) {
        return jobRepository.findByUserId(userId).stream()
                .map(this::toDTO)
                .collect(Collectors.toList());
    }

    private JobStatusDTO toDTO(ReportJob job) {
        return JobStatusDTO.builder()
                .id(job.getId())
                .jobNo(job.getJobNo())
                .l5ReportNo(job.getL5ReportNo())
                .userId(job.getUserId())
                .clientType(job.getClientType())
                .businessType(job.getBusinessType())
                .status(job.getStatus())
                .retryCount(job.getRetryCount())
                .errorMessage(job.getErrorMessage())
                .formatJobId(job.getFormatJobId())
                .startedAt(job.getStartedAt())
                .completedAt(job.getCompletedAt())
                .createdAt(job.getCreatedAt())
                .build();
    }

    private String toJson(Object obj) {
        if (obj == null) return null;
        try {
            return objectMapper.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            log.warn("Failed to serialize object to JSON: {}", e.getMessage());
            return "{}";
        }
    }

    private String truncate(String s, int max) {
        if (s == null) return null;
        return s.length() > max ? s.substring(0, max) : s;
    }
}
