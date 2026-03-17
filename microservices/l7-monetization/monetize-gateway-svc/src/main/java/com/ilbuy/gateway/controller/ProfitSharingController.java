package com.ilbuy.gateway.controller;

import com.ilbuy.gateway.domain.ProfitSharingRecord;
import com.ilbuy.gateway.dto.ProfitSharingRequest;
import com.ilbuy.gateway.service.ProfitSharingService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * Profit-sharing (分账) API.
 * Internal only — accessed by b-monetize-svc and billing-svc after payment confirmation.
 */
@RestController
@RequestMapping("/internal/v1/profit-sharing")
@RequiredArgsConstructor
@Slf4j
public class ProfitSharingController {

    private final ProfitSharingService profitSharingService;

    /** Initiate profit sharing for a completed payment. */
    @PostMapping
    public ResponseEntity<ProfitSharingRecord> initiate(@Valid @RequestBody ProfitSharingRequest req) {
        log.info("[ProfitSharingAPI] Initiate: paymentNo={}", req.getPaymentNo());
        return ResponseEntity.ok(profitSharingService.initiate(req));
    }

    /** Query sharing result by internal order number. */
    @GetMapping("/{orderNo}")
    public ResponseEntity<ProfitSharingRecord> query(@PathVariable String orderNo) {
        return ResponseEntity.ok(profitSharingService.query(orderNo));
    }

    /** List all sharing records for a payment. */
    @GetMapping("/by-payment/{paymentNo}")
    public ResponseEntity<List<ProfitSharingRecord>> queryByPayment(@PathVariable String paymentNo) {
        return ResponseEntity.ok(profitSharingService.queryByPayment(paymentNo));
    }
}
