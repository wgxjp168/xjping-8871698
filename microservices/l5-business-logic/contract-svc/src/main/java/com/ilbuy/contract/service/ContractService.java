package com.ilbuy.contract.service;

import com.ilbuy.contract.esign.ESignService;
import com.ilbuy.contract.model.dto.*;
import com.ilbuy.contract.model.entity.Contract;
import com.ilbuy.contract.model.entity.ContractSignature;
import com.ilbuy.contract.model.enums.ContractStatus;
import com.ilbuy.contract.model.enums.ContractType;
import com.ilbuy.contract.repository.ContractRepository;
import com.ilbuy.contract.repository.ContractSignatureRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Random;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class ContractService {

    private final ContractRepository contractRepository;
    private final ContractSignatureRepository contractSignatureRepository;
    private final ESignService eSignService;

    private static final Random RANDOM = new Random();
    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMdd");

    private static final String BUYER_ROLE = "BUYER";
    private static final String SUPPLIER_ROLE = "SUPPLIER";

    @Transactional
    public ContractDTO createContract(Long buyerUserId, CreateContractRequest request) {
        String contractNo = generateContractNo();
        String fileUrl = eSignService.generateContractFile(contractNo, request.getTitle());

        Contract contract = Contract.builder()
            .contractNo(contractNo)
            .orderId(request.getOrderId())
            .buyerUserId(buyerUserId)
            .supplierNo(request.getSupplierNo())
            .title(request.getTitle())
            .type(request.getType())
            .status(ContractStatus.DRAFT)
            .fileUrl(fileUrl)
            .expiresAt(request.getExpiresAt())
            .totalAmount(request.getTotalAmount())
            .build();

        contract = contractRepository.save(contract);
        log.info("Contract created: {}", contractNo);
        return toDTO(contract);
    }

    @Transactional(readOnly = true)
    public PageResult<ContractDTO> listContracts(Long userId, ContractStatus status, ContractType type,
                                                  int page, int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<Contract> contractPage = contractRepository.findByUserIdAndFilters(userId, status, type, pageable);

        List<ContractDTO> content = contractPage.getContent().stream()
            .map(this::toDTO)
            .collect(Collectors.toList());

        return PageResult.<ContractDTO>builder()
            .content(content)
            .page(page)
            .size(size)
            .totalElements(contractPage.getTotalElements())
            .totalPages(contractPage.getTotalPages())
            .build();
    }

    @Transactional(readOnly = true)
    public ContractDTO getContractDetail(String contractNo) {
        Contract contract = findByContractNo(contractNo);
        return toDTO(contract);
    }

    @Transactional
    public ContractDTO signContract(String contractNo, Long signerUserId, String signerRole,
                                    SignContractRequest request) {
        Contract contract = findByContractNo(contractNo);

        if (contract.getStatus() == ContractStatus.TERMINATED) {
            throw new IllegalStateException("合同已终止，无法签署");
        }
        if (contract.getStatus() == ContractStatus.SIGNED) {
            throw new IllegalStateException("合同已签署完毕");
        }

        // Determine signer role based on the user
        String resolvedRole = resolveSignerRole(contract, signerUserId, signerRole);

        if (contractSignatureRepository.existsByContractIdAndSignerRole(contract.getId(), resolvedRole)) {
            throw new IllegalStateException(resolvedRole + " 已签署，不能重复签署");
        }

        ContractSignature signature = ContractSignature.builder()
            .contractId(contract.getId())
            .signerUserId(signerUserId)
            .signerRole(resolvedRole)
            .signMethod(request.getSignMethod())
            .signatureImageUrl(request.getSignatureImageUrl())
            .build();

        contractSignatureRepository.save(signature);

        // Update contract status to PENDING_SIGN if it was DRAFT
        if (contract.getStatus() == ContractStatus.DRAFT) {
            contract.setStatus(ContractStatus.PENDING_SIGN);
        }

        // Check if both BUYER and SUPPLIER have signed
        boolean buyerSigned = contractSignatureRepository.existsByContractIdAndSignerRole(
            contract.getId(), BUYER_ROLE);
        boolean supplierSigned = contractSignatureRepository.existsByContractIdAndSignerRole(
            contract.getId(), SUPPLIER_ROLE);

        if (buyerSigned && supplierSigned) {
            String sealedUrl = eSignService.applyDigitalSeal(contractNo);
            contract.setFileUrl(sealedUrl);
            contract.setStatus(ContractStatus.SIGNED);
            contract.setSignedAt(LocalDateTime.now());
            log.info("Contract {} fully signed and sealed", contractNo);
        }

        contract = contractRepository.save(contract);
        return toDTO(contract);
    }

    @Transactional
    public ContractDTO terminateContract(String contractNo) {
        Contract contract = findByContractNo(contractNo);

        if (contract.getStatus() == ContractStatus.TERMINATED) {
            throw new IllegalStateException("合同已处于终止状态");
        }

        contract.setStatus(ContractStatus.TERMINATED);
        contract = contractRepository.save(contract);
        log.info("Contract {} terminated", contractNo);
        return toDTO(contract);
    }

    private String resolveSignerRole(Contract contract, Long signerUserId, String requestedRole) {
        // If requestedRole is provided by the caller (e.g. via header or request body), use it.
        // Otherwise determine from contract data: buyerUserId maps to BUYER; anything else is SUPPLIER.
        if (requestedRole != null && !requestedRole.isBlank()) {
            return requestedRole.toUpperCase();
        }
        if (contract.getBuyerUserId().equals(signerUserId)) {
            return BUYER_ROLE;
        }
        return SUPPLIER_ROLE;
    }

    private Contract findByContractNo(String contractNo) {
        return contractRepository.findByContractNo(contractNo)
            .orElseThrow(() -> new IllegalArgumentException("合同不存在: " + contractNo));
    }

    private String generateContractNo() {
        String date = LocalDateTime.now().format(DATE_FORMATTER);
        int random = RANDOM.nextInt(100_000_000);
        return String.format("CON%s%08d", date, random);
    }

    private ContractDTO toDTO(Contract contract) {
        return ContractDTO.builder()
            .id(contract.getId())
            .contractNo(contract.getContractNo())
            .orderId(contract.getOrderId())
            .buyerUserId(contract.getBuyerUserId())
            .supplierNo(contract.getSupplierNo())
            .title(contract.getTitle())
            .type(contract.getType())
            .status(contract.getStatus())
            .fileUrl(contract.getFileUrl())
            .signedAt(contract.getSignedAt())
            .expiresAt(contract.getExpiresAt())
            .totalAmount(contract.getTotalAmount())
            .createdAt(contract.getCreatedAt())
            .updatedAt(contract.getUpdatedAt())
            .build();
    }
}
