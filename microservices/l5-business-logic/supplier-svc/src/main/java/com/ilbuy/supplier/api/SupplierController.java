package com.ilbuy.supplier.api;

import com.ilbuy.supplier.model.dto.*;
import com.ilbuy.supplier.model.enums.SupplierStatus;
import com.ilbuy.supplier.service.SupplierService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/suppliers")
@RequiredArgsConstructor
public class SupplierController {

    private final SupplierService supplierService;

    /**
     * POST /api/v1/suppliers — create supplier (ADMIN/B2B_MANAGER)
     */
    @PostMapping
    @PreAuthorize("hasAnyRole('ADMIN', 'B2B_MANAGER')")
    public ResponseEntity<SupplierDTO> createSupplier(
        @Valid @RequestBody CreateSupplierRequest request
    ) {
        SupplierDTO dto = supplierService.createSupplier(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(dto);
    }

    /**
     * GET /api/v1/suppliers — list suppliers (paginated, filter by status/keyword)
     */
    @GetMapping
    public ResponseEntity<PageResult<SupplierDTO>> listSuppliers(
        @RequestParam(required = false) SupplierStatus status,
        @RequestParam(required = false) String keyword,
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "20") int size
    ) {
        PageResult<SupplierDTO> result = supplierService.listSuppliers(status, keyword, page, size);
        return ResponseEntity.ok(result);
    }

    /**
     * GET /api/v1/suppliers/{supplierNo} — get supplier detail (docs + score history)
     */
    @GetMapping("/{supplierNo}")
    public ResponseEntity<SupplierDetailDTO> getSupplierDetail(
        @PathVariable String supplierNo
    ) {
        SupplierDetailDTO detail = supplierService.getSupplierDetail(supplierNo);
        return ResponseEntity.ok(detail);
    }

    /**
     * PUT /api/v1/suppliers/{supplierNo} — update supplier info (ADMIN/B2B_MANAGER)
     */
    @PutMapping("/{supplierNo}")
    @PreAuthorize("hasAnyRole('ADMIN', 'B2B_MANAGER')")
    public ResponseEntity<SupplierDTO> updateSupplier(
        @PathVariable String supplierNo,
        @Valid @RequestBody UpdateSupplierRequest request
    ) {
        SupplierDTO dto = supplierService.updateSupplier(supplierNo, request);
        return ResponseEntity.ok(dto);
    }

    /**
     * PUT /api/v1/suppliers/{supplierNo}/status — change status (ADMIN)
     */
    @PutMapping("/{supplierNo}/status")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<SupplierDTO> changeStatus(
        @PathVariable String supplierNo,
        @Valid @RequestBody ChangeStatusRequest request
    ) {
        SupplierDTO dto = supplierService.changeStatus(supplierNo, request.getStatus());
        return ResponseEntity.ok(dto);
    }

    /**
     * POST /api/v1/suppliers/{supplierNo}/documents — add qualification document
     */
    @PostMapping("/{supplierNo}/documents")
    @PreAuthorize("hasAnyRole('ADMIN', 'B2B_MANAGER')")
    public ResponseEntity<SupplierDocumentDTO> addDocument(
        @PathVariable String supplierNo,
        @Valid @RequestBody AddDocumentRequest request
    ) {
        SupplierDocumentDTO dto = supplierService.addDocument(supplierNo, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(dto);
    }

    /**
     * DELETE /api/v1/suppliers/{supplierNo}/documents/{docId} — remove document
     */
    @DeleteMapping("/{supplierNo}/documents/{docId}")
    @PreAuthorize("hasAnyRole('ADMIN', 'B2B_MANAGER')")
    public ResponseEntity<Void> removeDocument(
        @PathVariable String supplierNo,
        @PathVariable Long docId
    ) {
        supplierService.removeDocument(supplierNo, docId);
        return ResponseEntity.noContent().build();
    }

    /**
     * GET /api/v1/suppliers/{supplierNo}/scores — get cooperation score history (paginated)
     */
    @GetMapping("/{supplierNo}/scores")
    public ResponseEntity<PageResult<CooperationScoreDTO>> getScores(
        @PathVariable String supplierNo,
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "20") int size
    ) {
        PageResult<CooperationScoreDTO> result = supplierService.getScores(supplierNo, page, size);
        return ResponseEntity.ok(result);
    }

    /**
     * POST /api/v1/suppliers/{supplierNo}/scores — add cooperation evaluation
     */
    @PostMapping("/{supplierNo}/scores")
    public ResponseEntity<CooperationScoreDTO> addScore(
        @PathVariable String supplierNo,
        @Valid @RequestBody AddScoreRequest request,
        Authentication authentication
    ) {
        Long userId = (Long) authentication.getPrincipal();
        CooperationScoreDTO dto = supplierService.addScore(supplierNo, userId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(dto);
    }
}
