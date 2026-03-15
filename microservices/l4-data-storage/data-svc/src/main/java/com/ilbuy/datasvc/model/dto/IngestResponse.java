package com.ilbuy.datasvc.model.dto;

import lombok.Builder;
import lombok.Data;

import java.time.Instant;

@Data
@Builder
public class IngestResponse {
    private String jobId;
    private String sessionId;
    private int total;
    private int saved;
    private int failed;
    private long durationMs;
    private Instant processedAt;
    private String status;
}
