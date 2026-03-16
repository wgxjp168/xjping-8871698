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

    // Post-construct map for O(1) lookup
    @jakarta.annotation.PostConstruct
    public void initStrategyMap() {
        strategyMap = strategies.stream()
                .collect(Collectors.toMap(ReportGeneratorStrategy::supports, Function.identity()));
        log.info("Loaded {} report generator strategies: {}", strategyMap.size(), strategyMap.keySet());
    }

    /**
     * Called by MQ consumer. Async so the consumer ACK is fast.
     */
    @Async("reportGeneratorExecutor")
    @Transactional
    public void processGenerateEvent(ReportGenerateEvent event) {
        String jobNo = "RG-" + UUID.randomUUID().toString().replace("-", "").substring(0, 16).toUpperCase();

        // Idempotency check
        if (jobRepository.findByL5ReportNo(event.getL5ReportNo()).isPresent()) {
            log.warn("[Generator] Duplicate event for l5ReportNo={}, skipping", event.getL5ReportNo());
            return;
        }

        ReportJob job = ReportJob.builder()
                .jobNo(jobNo)
                .l5ReportNo(event.getL5ReportNo())
                .userId(event.getUserId())
                .clientType(event.getClientType())
                .businessType(event.getBusinessType())
                .brandId(event.getBrandId())
                .categoryId(event.getCategoryId())
                .parameters(toJson(event.getParameters()))
                .status(JobStatus.PROCESSING)
                .startedAt(OffsetDateTime.now())
                .build();
        jobRepository.save(job);

        try {
            ReportGeneratorStrategy strategy = strategyMap.get(event.getClientType());
            if (strategy == null) {
                throw new IllegalArgumentException("No generator strategy for clientType=" + event.getClientType());
            }

            GeneratedReport generated = strategy.generate(event);
            generated = GeneratedReport.builder()
                    .jobNo(jobNo)
                    .l5ReportNo(generated.getL5ReportNo())
                    .userId(generated.getUserId())
                    .title(generated.getTitle())
                    .clientType(generated.getClientType())
                    .businessType(generated.getBusinessType())
                    .brandId(generated.getBrandId())
                    .categoryId(generated.getCategoryId())
                    .sections(generated.getSections())
                    .metadata(generated.getMetadata())
                    .generatedAt(generated.getGeneratedAt())
                    .generateHtml(generated.isGenerateHtml())
                    .generatePdf(generated.isGeneratePdf())
                    .generateExcel(generated.isGenerateExcel())
                    .deliverEmail(generated.isDeliverEmail())
                    .emailAddress(generated.getEmailAddress())
                    .deliverWechat(generated.isDeliverWechat())
                    .wechatOpenId(generated.getWechatOpenId())
                    .deliverApp(generated.isDeliverApp())
                    .appDeviceToken(generated.getAppDeviceToken())
                    .build();

            // Persist sections
            saveSections(job, generated.getSections());

            // Forward to format-output-svc
            Long formatJobId = formatOutputClient.submitFormatJob(generated);

            // Mark complete
            job.setStatus(JobStatus.COMPLETED);
            job.setResultJson(toJson(Map.of("sectionCount", generated.getSections().size())));
            job.setFormatJobId(formatJobId);
            job.setCompletedAt(OffsetDateTime.now());
            jobRepository.save(job);

            log.info("[Generator] Job {} completed, forwarded to format-svc formatJobId={}", jobNo, formatJobId);

        } catch (Exception e) {
            log.error("[Generator] Job {} failed: {}", jobNo, e.getMessage(), e);
            job.setStatus(JobStatus.FAILED);
            job.setErrorMessage(e.getMessage());
            job.setRetryCount(job.getRetryCount() + 1);
            jobRepository.save(job);
            throw new RuntimeException("Report generation failed: " + e.getMessage(), e);
        }
    }

    private void saveSections(ReportJob job, List<ReportSectionData> sections) {
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
            log.warn("Failed to serialize object: {}", e.getMessage());
            return "{}";
        }
    }
}
