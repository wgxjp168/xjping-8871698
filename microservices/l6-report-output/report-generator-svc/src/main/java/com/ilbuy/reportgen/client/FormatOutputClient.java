package com.ilbuy.reportgen.client;

import com.ilbuy.reportgen.model.dto.GeneratedReport;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.Duration;
import java.util.Map;

/**
 * HTTP client for L6 format-output-svc – submits generated report for multi-format rendering.
 */
@Component
@Slf4j
public class FormatOutputClient {

    private final WebClient webClient;

    public FormatOutputClient(@Value("${l6.format-output-svc.base-url}") String baseUrl,
                              @Value("${l6.format-output-svc.timeout:60000}") long timeoutMs) {
        this.webClient = WebClient.builder()
                .baseUrl(baseUrl)
                .defaultHeader("X-Internal-Service", "report-generator-svc")
                .build();
    }

    /**
     * Submit a generated report to format-output-svc.
     * @return formatJobId from format-output-svc
     */
    @SuppressWarnings("unchecked")
    public Long submitFormatJob(GeneratedReport report) {
        log.info("[FormatClient] Submitting format job for jobNo={}", report.getJobNo());
        try {
            Map<String, Object> response = webClient.post()
                    .uri("/internal/v1/format-jobs")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(report)
                    .retrieve()
                    .bodyToMono(Map.class)
                    .timeout(Duration.ofSeconds(60))
                    .block();

            if (response != null && response.containsKey("formatJobId")) {
                Long formatJobId = Long.valueOf(response.get("formatJobId").toString());
                log.info("[FormatClient] Format job created: formatJobId={}", formatJobId);
                return formatJobId;
            }
            return -1L;
        } catch (Exception e) {
            log.error("[FormatClient] Failed to submit format job for {}: {}", report.getJobNo(), e.getMessage());
            return -1L;
        }
    }
}
