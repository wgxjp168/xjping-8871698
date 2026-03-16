package com.ilbuy.reportgen.client;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

/**
 * HTTP client for L5 report-svc – fetches enriched report data by reportNo.
 */
@Component
@Slf4j
public class L5ReportClient {

    private final WebClient webClient;

    public L5ReportClient(@Value("${l5.report-svc.base-url}") String baseUrl,
                          @Value("${l5.report-svc.timeout:30000}") long timeoutMs) {
        this.webClient = WebClient.builder()
                .baseUrl(baseUrl)
                .defaultHeader("X-Internal-Service", "report-generator-svc")
                .build();
    }

    /**
     * Fetch enriched report data from L5 by l5ReportNo.
     * Returns enriched data map (supplier info, pricing data, market data).
     * Falls back to empty map on error to allow partial generation.
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> fetchReportData(String l5ReportNo) {
        log.debug("[L5Client] Fetching data for reportNo={}", l5ReportNo);
        try {
            Map<String, Object> response = webClient.get()
                    .uri("/internal/v1/reports/{reportNo}/data", l5ReportNo)
                    .retrieve()
                    .bodyToMono(Map.class)
                    .timeout(Duration.ofSeconds(30))
                    .block();
            if (response == null) return new HashMap<>();
            log.debug("[L5Client] Got {} fields for reportNo={}", response.size(), l5ReportNo);
            return response;
        } catch (WebClientResponseException e) {
            log.warn("[L5Client] HTTP {} for reportNo={}: {}", e.getStatusCode(), l5ReportNo, e.getMessage());
            return new HashMap<>();
        } catch (Exception e) {
            log.warn("[L5Client] Error fetching l5 data for reportNo={}: {}", l5ReportNo, e.getMessage());
            return new HashMap<>();
        }
    }
}
