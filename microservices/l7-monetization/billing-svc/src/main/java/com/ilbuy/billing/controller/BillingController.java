package com.ilbuy.billing.controller;

import com.ilbuy.billing.dto.CreateRefundRequest;
import com.ilbuy.billing.dto.InvoiceResponse;
import com.ilbuy.billing.dto.RefundResponse;
import com.ilbuy.billing.service.BillingService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/billing")
@RequiredArgsConstructor
@Slf4j
public class BillingController {

    private final BillingService billingService;

    /**
     * GET /api/v1/billing/invoices/{invoiceNo}
     * Retrieve invoice by invoice number.
     */
    @GetMapping("/invoices/{invoiceNo}")
    public ResponseEntity<InvoiceResponse> getInvoice(@PathVariable String invoiceNo) {
        log.debug("GET invoice: {}", invoiceNo);
        return ResponseEntity.ok(billingService.getInvoice(invoiceNo));
    }

    /**
     * POST /api/v1/billing/refunds
     * Create a refund request.
     */
    @PostMapping("/refunds")
    public ResponseEntity<RefundResponse> createRefund(@Valid @RequestBody CreateRefundRequest request) {
        log.debug("POST refund for order: {}", request.getOriginalOrderNo());
        return ResponseEntity.ok(billingService.createRefund(request));
    }

    /**
     * GET /api/v1/billing/refunds/{refundNo}
     * Retrieve refund by refund number.
     */
    @GetMapping("/refunds/{refundNo}")
    public ResponseEntity<RefundResponse> getRefund(@PathVariable String refundNo) {
        log.debug("GET refund: {}", refundNo);
        return ResponseEntity.ok(billingService.getRefund(refundNo));
    }
}
