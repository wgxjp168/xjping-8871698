package com.ilbuy.bmonetize.controller;

import com.ilbuy.bmonetize.service.ApiQuotaCheckService;
import com.ilbuy.bmonetize.service.ApiQuotaCheckService.QuotaResult;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * Internal quota check/gate endpoint.
 * Called by the API gateway (Kong/Nginx) or upstream services via service mesh
 * to enforce quota before proxying the actual recommendation API request.
 *
 * Returns 200 if allowed, 429 if rate-limited or quota exhausted.
 */
@RestController
@RequestMapping("/internal/v1/quota")
@RequiredArgsConstructor
public class ApiQuotaController {

    private final ApiQuotaCheckService quotaCheckService;

    /**
     * Gate-check: consume one quota unit and return allow/deny decision.
     * Call this BEFORE forwarding the upstream request.
     */
    @PostMapping("/check")
    public ResponseEntity<Map<String, Object>> check(
            @RequestParam Long corpId,
            @RequestParam(defaultValue = "recommend") String endpoint) {

        QuotaResult result = quotaCheckService.checkAndConsume(corpId, endpoint);

        Map<String, Object> body = Map.of(
            "allowed",    result.allowed(),
            "remaining",  result.remaining(),
            "denyReason", result.denyReason() != null ? result.denyReason().name() : ""
        );

        if (!result.allowed()) {
            return ResponseEntity.status(result.denyReason() == QuotaResult.DenyReason.RATE_LIMITED
                ? HttpStatus.TOO_MANY_REQUESTS : HttpStatus.PAYMENT_REQUIRED).body(body);
        }
        return ResponseEntity.ok(body);
    }

    /** Non-destructive peek at remaining quota. */
    @GetMapping("/peek")
    public ResponseEntity<Map<String, Object>> peek(@RequestParam Long corpId) {
        QuotaResult result = quotaCheckService.peek(corpId);
        return ResponseEntity.ok(Map.of(
            "allowed",   result.allowed(),
            "remaining", result.remaining()
        ));
    }
}
