package com.ilbuy.datasvc.api;

import com.ilbuy.datasvc.model.dto.IngestRequest;
import com.ilbuy.datasvc.model.dto.IngestResponse;
import com.ilbuy.datasvc.service.IngestService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * POST /ingest — 接收 L3 ETL 推送的商品数据批次
 */
@RestController
@RequestMapping("/ingest")
@RequiredArgsConstructor
@Slf4j
public class IngestController {

    private final IngestService ingestService;

    @PostMapping
    public ResponseEntity<IngestResponse> ingest(@Valid @RequestBody IngestRequest request) {
        log.info("\"Ingest request: jobId={} sessionId={} products={}\"",
            request.getJobId(), request.getSessionId(), request.getProducts().size());
        IngestResponse response = ingestService.ingest(request);
        return ResponseEntity.ok(response);
    }
}
