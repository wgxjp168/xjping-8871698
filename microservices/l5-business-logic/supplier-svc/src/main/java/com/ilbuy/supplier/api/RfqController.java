package com.ilbuy.supplier.api;

import com.ilbuy.supplier.model.dto.rfq.*;
import com.ilbuy.supplier.model.enums.RfqStatus;
import com.ilbuy.supplier.service.RfqService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/rfq")
@RequiredArgsConstructor
public class RfqController {

    private final RfqService rfqService;

    /**
     * POST /api/v1/rfq — create RFQ (B2B buyer; requires auth)
     */
    @PostMapping
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<RfqRequestDTO> createRfq(
        @Valid @RequestBody CreateRfqRequest request,
        Authentication authentication
    ) {
        Long buyerUserId = (Long) authentication.getPrincipal();
        RfqRequestDTO dto = rfqService.createRfq(buyerUserId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(dto);
    }

    /**
     * POST /api/v1/rfq/{rfqNo}/submit — submit RFQ to supplier (requires auth, owner)
     */
    @PostMapping("/{rfqNo}/submit")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<RfqRequestDTO> submitRfq(
        @PathVariable String rfqNo,
        Authentication authentication
    ) {
        Long buyerUserId = (Long) authentication.getPrincipal();
        RfqRequestDTO dto = rfqService.submitRfq(buyerUserId, rfqNo);
        return ResponseEntity.ok(dto);
    }

    /**
     * POST /api/v1/rfq/{rfqNo}/cancel — cancel RFQ (requires auth, owner)
     */
    @PostMapping("/{rfqNo}/cancel")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<RfqRequestDTO> cancelRfq(
        @PathVariable String rfqNo,
        Authentication authentication
    ) {
        Long buyerUserId = (Long) authentication.getPrincipal();
        RfqRequestDTO dto = rfqService.cancelRfq(buyerUserId, rfqNo);
        return ResponseEntity.ok(dto);
    }

    /**
     * GET /api/v1/rfq/buyer — list current user's RFQs as buyer (?status=&page=&size=)
     */
    @GetMapping("/buyer")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<RfqPageResult> getBuyerRfqs(
        @RequestParam(required = false) RfqStatus status,
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "20") int size,
        Authentication authentication
    ) {
        Long buyerUserId = (Long) authentication.getPrincipal();
        RfqPageResult result = rfqService.getBuyerRfqs(buyerUserId, status, page, size);
        return ResponseEntity.ok(result);
    }

    /**
     * GET /api/v1/rfq/supplier/{supplierNo} — list RFQs for a supplier (?status=&page=&size=)
     */
    @GetMapping("/supplier/{supplierNo}")
    @PreAuthorize("hasAnyRole('ADMIN', 'B2B_MANAGER') or isAuthenticated()")
    public ResponseEntity<RfqPageResult> getSupplierRfqs(
        @PathVariable String supplierNo,
        @RequestParam(required = false) RfqStatus status,
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "20") int size
    ) {
        RfqPageResult result = rfqService.getSupplierRfqs(supplierNo, status, page, size);
        return ResponseEntity.ok(result);
    }

    /**
     * GET /api/v1/rfq/{rfqNo} — get RFQ detail
     */
    @GetMapping("/{rfqNo}")
    public ResponseEntity<RfqRequestDTO> getRfqDetail(
        @PathVariable String rfqNo
    ) {
        RfqRequestDTO dto = rfqService.getRfqDetail(rfqNo);
        return ResponseEntity.ok(dto);
    }

    /**
     * POST /api/v1/rfq/{rfqNo}/quote — supplier submits quotation (?supplierNo=)
     */
    @PostMapping("/{rfqNo}/quote")
    public ResponseEntity<RfqRequestDTO> submitQuote(
        @PathVariable String rfqNo,
        @RequestParam String supplierNo,
        @Valid @RequestBody SubmitQuoteRequest request
    ) {
        RfqRequestDTO dto = rfqService.submitQuote(supplierNo, rfqNo, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(dto);
    }

    /**
     * POST /api/v1/rfq/{rfqNo}/accept — buyer accepts quote (requires auth, owner)
     */
    @PostMapping("/{rfqNo}/accept")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<RfqRequestDTO> acceptQuote(
        @PathVariable String rfqNo,
        Authentication authentication
    ) {
        Long buyerUserId = (Long) authentication.getPrincipal();
        RfqRequestDTO dto = rfqService.acceptQuote(buyerUserId, rfqNo);
        return ResponseEntity.ok(dto);
    }

    /**
     * POST /api/v1/rfq/{rfqNo}/reject — buyer rejects quote (requires auth, owner)
     */
    @PostMapping("/{rfqNo}/reject")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<RfqRequestDTO> rejectQuote(
        @PathVariable String rfqNo,
        Authentication authentication
    ) {
        Long buyerUserId = (Long) authentication.getPrincipal();
        RfqRequestDTO dto = rfqService.rejectQuote(buyerUserId, rfqNo);
        return ResponseEntity.ok(dto);
    }
}
