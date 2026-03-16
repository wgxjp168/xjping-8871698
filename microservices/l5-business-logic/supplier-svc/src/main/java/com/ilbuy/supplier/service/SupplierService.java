package com.ilbuy.supplier.service;

import com.ilbuy.supplier.model.dto.*;
import com.ilbuy.supplier.model.entity.CooperationScore;
import com.ilbuy.supplier.model.entity.Supplier;
import com.ilbuy.supplier.model.entity.SupplierDocument;
import com.ilbuy.supplier.model.enums.SupplierStatus;
import com.ilbuy.supplier.repository.CooperationScoreRepository;
import com.ilbuy.supplier.repository.SupplierDocumentRepository;
import com.ilbuy.supplier.repository.SupplierRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Random;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class SupplierService {

    private final SupplierRepository supplierRepository;
    private final SupplierDocumentRepository supplierDocumentRepository;
    private final CooperationScoreRepository cooperationScoreRepository;

    private static final Random RANDOM = new Random();
    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMdd");

    @Transactional
    public SupplierDTO createSupplier(CreateSupplierRequest request) {
        if (supplierRepository.existsByBusinessLicense(request.getBusinessLicense())) {
            throw new IllegalArgumentException("营业执照号已存在: " + request.getBusinessLicense());
        }

        String supplierNo = generateSupplierNo();
        Supplier supplier = Supplier.builder()
            .supplierNo(supplierNo)
            .companyName(request.getCompanyName())
            .contactName(request.getContactName())
            .contactEmail(request.getContactEmail())
            .contactPhone(request.getContactPhone())
            .businessLicense(request.getBusinessLicense())
            .status(SupplierStatus.PENDING)
            .averageScore(BigDecimal.ZERO)
            .totalCoopCount(0)
            .build();

        supplier = supplierRepository.save(supplier);
        log.info("Supplier created: {}", supplierNo);
        return toDTO(supplier);
    }

    @Transactional(readOnly = true)
    public PageResult<SupplierDTO> listSuppliers(SupplierStatus status, String keyword, int page, int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<Supplier> supplierPage = supplierRepository.findByStatusAndKeyword(status, keyword, pageable);

        List<SupplierDTO> content = supplierPage.getContent().stream()
            .map(this::toDTO)
            .collect(Collectors.toList());

        return PageResult.<SupplierDTO>builder()
            .content(content)
            .page(page)
            .size(size)
            .totalElements(supplierPage.getTotalElements())
            .totalPages(supplierPage.getTotalPages())
            .build();
    }

    @Transactional(readOnly = true)
    public SupplierDetailDTO getSupplierDetail(String supplierNo) {
        Supplier supplier = findBySupplierNo(supplierNo);
        List<SupplierDocument> documents = supplierDocumentRepository.findBySupplierId(supplier.getId());
        Page<CooperationScore> scores = cooperationScoreRepository.findBySupplierId(
            supplier.getId(), PageRequest.of(0, 10, Sort.by(Sort.Direction.DESC, "scoredAt")));

        return SupplierDetailDTO.builder()
            .supplier(toDTO(supplier))
            .documents(documents.stream().map(this::toDocumentDTO).collect(Collectors.toList()))
            .scores(scores.getContent().stream().map(this::toScoreDTO).collect(Collectors.toList()))
            .build();
    }

    @Transactional
    public SupplierDTO updateSupplier(String supplierNo, UpdateSupplierRequest request) {
        Supplier supplier = findBySupplierNo(supplierNo);

        if (request.getCompanyName() != null) {
            supplier.setCompanyName(request.getCompanyName());
        }
        if (request.getContactName() != null) {
            supplier.setContactName(request.getContactName());
        }
        if (request.getContactEmail() != null) {
            supplier.setContactEmail(request.getContactEmail());
        }
        if (request.getContactPhone() != null) {
            supplier.setContactPhone(request.getContactPhone());
        }

        supplier = supplierRepository.save(supplier);
        log.info("Supplier updated: {}", supplierNo);
        return toDTO(supplier);
    }

    @Transactional
    public SupplierDTO changeStatus(String supplierNo, SupplierStatus newStatus) {
        Supplier supplier = findBySupplierNo(supplierNo);
        supplier.setStatus(newStatus);
        supplier = supplierRepository.save(supplier);
        log.info("Supplier {} status changed to {}", supplierNo, newStatus);
        return toDTO(supplier);
    }

    @Transactional
    public SupplierDocumentDTO addDocument(String supplierNo, AddDocumentRequest request) {
        Supplier supplier = findBySupplierNo(supplierNo);

        SupplierDocument document = SupplierDocument.builder()
            .supplierId(supplier.getId())
            .docType(request.getDocType())
            .docName(request.getDocName())
            .fileUrl(request.getFileUrl())
            .expiresAt(request.getExpiresAt())
            .build();

        document = supplierDocumentRepository.save(document);
        log.info("Document added for supplier {}: {}", supplierNo, document.getId());
        return toDocumentDTO(document);
    }

    @Transactional
    public void removeDocument(String supplierNo, Long docId) {
        Supplier supplier = findBySupplierNo(supplierNo);
        SupplierDocument document = supplierDocumentRepository
            .findByIdAndSupplierId(docId, supplier.getId())
            .orElseThrow(() -> new IllegalArgumentException("文件不存在: " + docId));

        supplierDocumentRepository.delete(document);
        log.info("Document {} removed from supplier {}", docId, supplierNo);
    }

    @Transactional(readOnly = true)
    public PageResult<CooperationScoreDTO> getScores(String supplierNo, int page, int size) {
        Supplier supplier = findBySupplierNo(supplierNo);
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "scoredAt"));
        Page<CooperationScore> scorePage = cooperationScoreRepository.findBySupplierId(supplier.getId(), pageable);

        List<CooperationScoreDTO> content = scorePage.getContent().stream()
            .map(this::toScoreDTO)
            .collect(Collectors.toList());

        return PageResult.<CooperationScoreDTO>builder()
            .content(content)
            .page(page)
            .size(size)
            .totalElements(scorePage.getTotalElements())
            .totalPages(scorePage.getTotalPages())
            .build();
    }

    @Transactional
    public CooperationScoreDTO addScore(String supplierNo, Long scoreBy, AddScoreRequest request) {
        Supplier supplier = findBySupplierNo(supplierNo);

        BigDecimal overallScore = request.getQualityScore()
            .add(request.getDeliveryScore())
            .add(request.getServiceScore())
            .divide(BigDecimal.valueOf(3), 2, RoundingMode.HALF_UP);

        CooperationScore score = CooperationScore.builder()
            .supplierId(supplier.getId())
            .orderId(request.getOrderId())
            .scoreBy(scoreBy)
            .qualityScore(request.getQualityScore())
            .deliveryScore(request.getDeliveryScore())
            .serviceScore(request.getServiceScore())
            .overallScore(overallScore)
            .comment(request.getComment())
            .build();

        score = cooperationScoreRepository.save(score);

        // Recalculate average score
        BigDecimal avgScore = cooperationScoreRepository.calculateAverageScoreBySupplierId(supplier.getId());
        long coopCount = cooperationScoreRepository.countBySupplierId(supplier.getId());

        supplier.setAverageScore(avgScore != null ? avgScore.setScale(2, RoundingMode.HALF_UP) : BigDecimal.ZERO);
        supplier.setTotalCoopCount((int) coopCount);
        supplierRepository.save(supplier);

        log.info("Score added for supplier {}: overall={}", supplierNo, overallScore);
        return toScoreDTO(score);
    }

    private Supplier findBySupplierNo(String supplierNo) {
        return supplierRepository.findBySupplierNo(supplierNo)
            .orElseThrow(() -> new IllegalArgumentException("供应商不存在: " + supplierNo));
    }

    private String generateSupplierNo() {
        String date = LocalDateTime.now().format(DATE_FORMATTER);
        int random = RANDOM.nextInt(1_000_000);
        return String.format("SUP%s%06d", date, random);
    }

    private SupplierDTO toDTO(Supplier supplier) {
        return SupplierDTO.builder()
            .id(supplier.getId())
            .supplierNo(supplier.getSupplierNo())
            .companyName(supplier.getCompanyName())
            .contactName(supplier.getContactName())
            .contactEmail(supplier.getContactEmail())
            .contactPhone(supplier.getContactPhone())
            .businessLicense(supplier.getBusinessLicense())
            .status(supplier.getStatus())
            .averageScore(supplier.getAverageScore())
            .totalCoopCount(supplier.getTotalCoopCount())
            .createdAt(supplier.getCreatedAt())
            .updatedAt(supplier.getUpdatedAt())
            .build();
    }

    private SupplierDocumentDTO toDocumentDTO(SupplierDocument doc) {
        return SupplierDocumentDTO.builder()
            .id(doc.getId())
            .supplierId(doc.getSupplierId())
            .docType(doc.getDocType())
            .docName(doc.getDocName())
            .fileUrl(doc.getFileUrl())
            .expiresAt(doc.getExpiresAt())
            .uploadedAt(doc.getUploadedAt())
            .build();
    }

    private CooperationScoreDTO toScoreDTO(CooperationScore score) {
        return CooperationScoreDTO.builder()
            .id(score.getId())
            .supplierId(score.getSupplierId())
            .orderId(score.getOrderId())
            .scoreBy(score.getScoreBy())
            .qualityScore(score.getQualityScore())
            .deliveryScore(score.getDeliveryScore())
            .serviceScore(score.getServiceScore())
            .overallScore(score.getOverallScore())
            .comment(score.getComment())
            .scoredAt(score.getScoredAt())
            .build();
    }
}
