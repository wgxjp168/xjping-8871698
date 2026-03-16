package com.ilbuy.contract.api;

import com.ilbuy.contract.model.dto.*;
import com.ilbuy.contract.service.InvoiceService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/invoices")
@RequiredArgsConstructor
public class InvoiceController {

    private final InvoiceService invoiceService;

    /**
     * POST /api/v1/invoices — request invoice issuance (links to contract, status=PENDING)
     */
    @PostMapping
    public ResponseEntity<InvoiceDTO> createInvoice(
        @Valid @RequestBody CreateInvoiceRequest request,
        Authentication authentication
    ) {
        Long userId = (Long) authentication.getPrincipal();
        InvoiceDTO dto = invoiceService.createInvoice(userId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(dto);
    }

    /**
     * GET /api/v1/invoices — list user's invoices (paginated)
     */
    @GetMapping
    public ResponseEntity<PageResult<InvoiceDTO>> listInvoices(
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "20") int size,
        Authentication authentication
    ) {
        Long userId = (Long) authentication.getPrincipal();
        PageResult<InvoiceDTO> result = invoiceService.listInvoices(userId, page, size);
        return ResponseEntity.ok(result);
    }

    /**
     * GET /api/v1/invoices/{invoiceNo} — get invoice detail
     */
    @GetMapping("/{invoiceNo}")
    public ResponseEntity<InvoiceDTO> getInvoiceDetail(
        @PathVariable String invoiceNo
    ) {
        InvoiceDTO dto = invoiceService.getInvoiceDetail(invoiceNo);
        return ResponseEntity.ok(dto);
    }

    /**
     * POST /api/v1/invoices/{invoiceNo}/issue — issue invoice (ADMIN/FINANCE)
     * status → ISSUED, generate invoiceNo = "INV" + yyyyMMdd + 8-digit
     */
    @PostMapping("/{invoiceNo}/issue")
    @PreAuthorize("hasAnyRole('ADMIN', 'FINANCE')")
    public ResponseEntity<InvoiceDTO> issueInvoice(
        @PathVariable String invoiceNo
    ) {
        InvoiceDTO dto = invoiceService.issueInvoice(invoiceNo);
        return ResponseEntity.ok(dto);
    }

    /**
     * POST /api/v1/invoices/{invoiceNo}/mail — mark as mailed (ADMIN)
     * update trackingNo, status → MAILED
     */
    @PostMapping("/{invoiceNo}/mail")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<InvoiceDTO> mailInvoice(
        @PathVariable String invoiceNo,
        @Valid @RequestBody MailInvoiceRequest request
    ) {
        InvoiceDTO dto = invoiceService.mailInvoice(invoiceNo, request.getTrackingNo());
        return ResponseEntity.ok(dto);
    }

    /**
     * POST /api/v1/invoices/{invoiceNo}/void — void invoice (ADMIN)
     * status → VOID
     */
    @PostMapping("/{invoiceNo}/void")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<InvoiceDTO> voidInvoice(
        @PathVariable String invoiceNo
    ) {
        InvoiceDTO dto = invoiceService.voidInvoice(invoiceNo);
        return ResponseEntity.ok(dto);
    }
}
