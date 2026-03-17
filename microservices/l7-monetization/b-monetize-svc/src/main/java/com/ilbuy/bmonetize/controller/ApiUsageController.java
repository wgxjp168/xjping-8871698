package com.ilbuy.bmonetize.controller;

import com.ilbuy.bmonetize.domain.BSaasContract;
import com.ilbuy.bmonetize.dto.RecordApiUsageRequest;
import com.ilbuy.bmonetize.service.ApiUsageService;
import com.ilbuy.bmonetize.service.BMonetizeService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/internal/v1/api-usage")
@RequiredArgsConstructor
public class ApiUsageController {

    private final ApiUsageService apiUsageService;
    private final BMonetizeService bMonetizeService;

    @PostMapping
    public ResponseEntity<Void> recordUsage(@Valid @RequestBody RecordApiUsageRequest req) {
        apiUsageService.recordUsage(req);
        return ResponseEntity.accepted().build();
    }

    @GetMapping("/corps/{corpId}/monthly")
    public ResponseEntity<Map<String, Object>> getMonthlyUsage(
            @PathVariable Long corpId,
            @RequestParam(defaultValue = "") String period) {
        if (period.isBlank()) period = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM"));
        return ResponseEntity.ok(apiUsageService.getMonthlyUsage(corpId, period));
    }

    @GetMapping("/corps/{corpId}/contract")
    public ResponseEntity<BSaasContract> getActiveContract(@PathVariable Long corpId) {
        Optional<BSaasContract> contract = bMonetizeService.getActiveContract(corpId);
        return contract.map(ResponseEntity::ok).orElseGet(() -> ResponseEntity.notFound().build());
    }
}
