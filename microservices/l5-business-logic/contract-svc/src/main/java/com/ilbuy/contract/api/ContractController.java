package com.ilbuy.contract.api;

import com.ilbuy.contract.model.dto.*;
import com.ilbuy.contract.model.enums.ContractStatus;
import com.ilbuy.contract.model.enums.ContractType;
import com.ilbuy.contract.service.ContractService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/contracts")
@RequiredArgsConstructor
public class ContractController {

    private final ContractService contractService;

    /**
     * POST /api/v1/contracts — create contract (DRAFT status, generate PDF via ESignService mock)
     */
    @PostMapping
    public ResponseEntity<ContractDTO> createContract(
        @Valid @RequestBody CreateContractRequest request,
        Authentication authentication
    ) {
        Long userId = (Long) authentication.getPrincipal();
        ContractDTO dto = contractService.createContract(userId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(dto);
    }

    /**
     * GET /api/v1/contracts — list user's contracts (paginated, filter by status/type)
     */
    @GetMapping
    public ResponseEntity<PageResult<ContractDTO>> listContracts(
        @RequestParam(required = false) ContractStatus status,
        @RequestParam(required = false) ContractType type,
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "20") int size,
        Authentication authentication
    ) {
        Long userId = (Long) authentication.getPrincipal();
        PageResult<ContractDTO> result = contractService.listContracts(userId, status, type, page, size);
        return ResponseEntity.ok(result);
    }

    /**
     * GET /api/v1/contracts/{contractNo} — get contract detail
     */
    @GetMapping("/{contractNo}")
    public ResponseEntity<ContractDTO> getContractDetail(
        @PathVariable String contractNo
    ) {
        ContractDTO dto = contractService.getContractDetail(contractNo);
        return ResponseEntity.ok(dto);
    }

    /**
     * POST /api/v1/contracts/{contractNo}/sign — buyer/supplier sign contract
     * Both must sign → status becomes SIGNED, ContractSignature is recorded
     */
    @PostMapping("/{contractNo}/sign")
    public ResponseEntity<ContractDTO> signContract(
        @PathVariable String contractNo,
        @Valid @RequestBody SignContractRequest request,
        @RequestParam(required = false) String role,
        Authentication authentication
    ) {
        Long userId = (Long) authentication.getPrincipal();
        ContractDTO dto = contractService.signContract(contractNo, userId, role, request);
        return ResponseEntity.ok(dto);
    }

    /**
     * POST /api/v1/contracts/{contractNo}/terminate — terminate contract (ADMIN)
     */
    @PostMapping("/{contractNo}/terminate")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<ContractDTO> terminateContract(
        @PathVariable String contractNo
    ) {
        ContractDTO dto = contractService.terminateContract(contractNo);
        return ResponseEntity.ok(dto);
    }
}
