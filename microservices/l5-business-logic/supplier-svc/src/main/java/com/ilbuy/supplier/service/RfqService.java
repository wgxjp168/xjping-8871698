package com.ilbuy.supplier.service;

import com.ilbuy.supplier.model.dto.rfq.*;
import com.ilbuy.supplier.model.entity.RfqQuote;
import com.ilbuy.supplier.model.entity.RfqRequest;
import com.ilbuy.supplier.model.enums.RfqStatus;
import com.ilbuy.supplier.repository.RfqQuoteRepository;
import com.ilbuy.supplier.repository.RfqRequestRepository;
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
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Optional;
import java.util.Random;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class RfqService {

    private final RfqRequestRepository rfqRequestRepository;
    private final RfqQuoteRepository rfqQuoteRepository;
    private final SupplierRepository supplierRepository;

    private static final Random RANDOM = new Random();
    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMdd");

    @Transactional
    public RfqRequestDTO createRfq(Long buyerUserId, CreateRfqRequest req) {
        if (!supplierRepository.findBySupplierNo(req.getSupplierNo()).isPresent()) {
            throw new IllegalArgumentException("供应商不存在: " + req.getSupplierNo());
        }

        String rfqNo = generateRfqNo();

        RfqRequest rfqRequest = RfqRequest.builder()
            .rfqNo(rfqNo)
            .buyerUserId(buyerUserId)
            .supplierNo(req.getSupplierNo())
            .productDescription(req.getProductDescription())
            .canonicalId(req.getCanonicalId())
            .quantity(req.getQuantity())
            .unit(req.getUnit())
            .requiredDeliveryDate(req.getRequiredDeliveryDate())
            .deliveryAddress(req.getDeliveryAddress())
            .budgetAmount(req.getBudgetAmount())
            .status(RfqStatus.DRAFT)
            .buyerRemark(req.getBuyerRemark())
            .build();

        rfqRequest = rfqRequestRepository.save(rfqRequest);
        log.info("RFQ created: {} by buyer {}", rfqNo, buyerUserId);
        return toDTO(rfqRequest, null);
    }

    @Transactional
    public RfqRequestDTO submitRfq(Long buyerUserId, String rfqNo) {
        RfqRequest rfqRequest = findByRfqNo(rfqNo);
        validateOwner(rfqRequest, buyerUserId);

        if (rfqRequest.getStatus() != RfqStatus.DRAFT) {
            throw new IllegalStateException("只有草稿状态的询价单才能提交，当前状态: " + rfqRequest.getStatus());
        }

        rfqRequest.setStatus(RfqStatus.SUBMITTED);
        rfqRequest = rfqRequestRepository.save(rfqRequest);
        log.info("RFQ {} submitted by buyer {}", rfqNo, buyerUserId);
        return toDTO(rfqRequest, null);
    }

    @Transactional
    public RfqRequestDTO cancelRfq(Long buyerUserId, String rfqNo) {
        RfqRequest rfqRequest = findByRfqNo(rfqNo);
        validateOwner(rfqRequest, buyerUserId);

        if (rfqRequest.getStatus() != RfqStatus.DRAFT && rfqRequest.getStatus() != RfqStatus.SUBMITTED) {
            throw new IllegalStateException("只有草稿或已提交状态的询价单才能取消，当前状态: " + rfqRequest.getStatus());
        }

        rfqRequest.setStatus(RfqStatus.CANCELLED);
        rfqRequest = rfqRequestRepository.save(rfqRequest);
        log.info("RFQ {} cancelled by buyer {}", rfqNo, buyerUserId);
        return toDTO(rfqRequest, null);
    }

    @Transactional(readOnly = true)
    public RfqPageResult getBuyerRfqs(Long buyerUserId, RfqStatus status, int page, int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<RfqRequest> rfqPage;

        if (status != null) {
            rfqPage = rfqRequestRepository.findByBuyerUserIdAndStatus(buyerUserId, status, pageable);
        } else {
            rfqPage = rfqRequestRepository.findByBuyerUserId(buyerUserId, pageable);
        }

        List<RfqRequestDTO> content = rfqPage.getContent().stream()
            .map(rfq -> {
                Optional<RfqQuote> quote = rfqQuoteRepository.findByRfqId(rfq.getId());
                return toDTO(rfq, quote.orElse(null));
            })
            .collect(Collectors.toList());

        return RfqPageResult.builder()
            .content(content)
            .page(page)
            .size(size)
            .totalElements(rfqPage.getTotalElements())
            .totalPages(rfqPage.getTotalPages())
            .build();
    }

    @Transactional
    public RfqRequestDTO submitQuote(String supplierNo, String rfqNo, SubmitQuoteRequest req) {
        RfqRequest rfqRequest = findByRfqNo(rfqNo);

        if (!rfqRequest.getSupplierNo().equals(supplierNo)) {
            throw new IllegalArgumentException("该询价单不属于供应商: " + supplierNo);
        }

        if (rfqRequest.getStatus() != RfqStatus.SUBMITTED) {
            throw new IllegalStateException("只有已提交状态的询价单才能报价，当前状态: " + rfqRequest.getStatus());
        }

        BigDecimal totalAmount = req.getUnitPrice().multiply(BigDecimal.valueOf(rfqRequest.getQuantity()));

        RfqQuote quote = RfqQuote.builder()
            .rfqId(rfqRequest.getId())
            .supplierNo(supplierNo)
            .unitPrice(req.getUnitPrice())
            .totalAmount(totalAmount)
            .currency("CNY")
            .deliveryDays(req.getDeliveryDays())
            .validUntil(req.getValidUntil())
            .paymentTerms(req.getPaymentTerms())
            .supplierRemark(req.getSupplierRemark())
            .build();

        quote = rfqQuoteRepository.save(quote);

        rfqRequest.setStatus(RfqStatus.QUOTED);
        rfqRequest = rfqRequestRepository.save(rfqRequest);

        log.info("Quote submitted for RFQ {} by supplier {}", rfqNo, supplierNo);
        return toDTO(rfqRequest, quote);
    }

    @Transactional(readOnly = true)
    public RfqPageResult getSupplierRfqs(String supplierNo, RfqStatus status, int page, int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<RfqRequest> rfqPage;

        if (status != null) {
            rfqPage = rfqRequestRepository.findBySupplierNoAndStatus(supplierNo, status, pageable);
        } else {
            rfqPage = rfqRequestRepository.findBySupplierNo(supplierNo, pageable);
        }

        List<RfqRequestDTO> content = rfqPage.getContent().stream()
            .map(rfq -> {
                Optional<RfqQuote> quote = rfqQuoteRepository.findByRfqId(rfq.getId());
                return toDTO(rfq, quote.orElse(null));
            })
            .collect(Collectors.toList());

        return RfqPageResult.builder()
            .content(content)
            .page(page)
            .size(size)
            .totalElements(rfqPage.getTotalElements())
            .totalPages(rfqPage.getTotalPages())
            .build();
    }

    @Transactional
    public RfqRequestDTO acceptQuote(Long buyerUserId, String rfqNo) {
        RfqRequest rfqRequest = findByRfqNo(rfqNo);
        validateOwner(rfqRequest, buyerUserId);

        if (rfqRequest.getStatus() != RfqStatus.QUOTED) {
            throw new IllegalStateException("只有已报价状态的询价单才能接受报价，当前状态: " + rfqRequest.getStatus());
        }

        RfqQuote quote = rfqQuoteRepository.findByRfqId(rfqRequest.getId())
            .orElseThrow(() -> new IllegalStateException("询价单报价不存在: " + rfqNo));

        if (quote.getValidUntil().isBefore(LocalDate.now())) {
            throw new IllegalStateException("报价已过期，有效期至: " + quote.getValidUntil());
        }

        rfqRequest.setStatus(RfqStatus.ACCEPTED);
        rfqRequest = rfqRequestRepository.save(rfqRequest);
        log.info("Quote accepted for RFQ {} by buyer {}", rfqNo, buyerUserId);
        return toDTO(rfqRequest, quote);
    }

    @Transactional
    public RfqRequestDTO rejectQuote(Long buyerUserId, String rfqNo) {
        RfqRequest rfqRequest = findByRfqNo(rfqNo);
        validateOwner(rfqRequest, buyerUserId);

        if (rfqRequest.getStatus() != RfqStatus.QUOTED) {
            throw new IllegalStateException("只有已报价状态的询价单才能拒绝报价，当前状态: " + rfqRequest.getStatus());
        }

        rfqRequest.setStatus(RfqStatus.REJECTED);
        rfqRequest = rfqRequestRepository.save(rfqRequest);

        Optional<RfqQuote> quote = rfqQuoteRepository.findByRfqId(rfqRequest.getId());
        log.info("Quote rejected for RFQ {} by buyer {}", rfqNo, buyerUserId);
        return toDTO(rfqRequest, quote.orElse(null));
    }

    @Transactional(readOnly = true)
    public RfqRequestDTO getRfqDetail(String rfqNo) {
        RfqRequest rfqRequest = findByRfqNo(rfqNo);
        Optional<RfqQuote> quote = rfqQuoteRepository.findByRfqId(rfqRequest.getId());
        return toDTO(rfqRequest, quote.orElse(null));
    }

    private RfqRequest findByRfqNo(String rfqNo) {
        return rfqRequestRepository.findByRfqNo(rfqNo)
            .orElseThrow(() -> new IllegalArgumentException("询价单不存在: " + rfqNo));
    }

    private void validateOwner(RfqRequest rfqRequest, Long buyerUserId) {
        if (!rfqRequest.getBuyerUserId().equals(buyerUserId)) {
            throw new IllegalArgumentException("无权操作该询价单: " + rfqRequest.getRfqNo());
        }
    }

    private String generateRfqNo() {
        String date = LocalDateTime.now().format(DATE_FORMATTER);
        int random = RANDOM.nextInt(1_000_000);
        return String.format("RFQ%s%06d", date, random);
    }

    private RfqRequestDTO toDTO(RfqRequest rfq, RfqQuote quote) {
        return RfqRequestDTO.builder()
            .id(rfq.getId())
            .rfqNo(rfq.getRfqNo())
            .buyerUserId(rfq.getBuyerUserId())
            .supplierNo(rfq.getSupplierNo())
            .productDescription(rfq.getProductDescription())
            .canonicalId(rfq.getCanonicalId())
            .quantity(rfq.getQuantity())
            .unit(rfq.getUnit())
            .requiredDeliveryDate(rfq.getRequiredDeliveryDate())
            .deliveryAddress(rfq.getDeliveryAddress())
            .budgetAmount(rfq.getBudgetAmount())
            .status(rfq.getStatus())
            .buyerRemark(rfq.getBuyerRemark())
            .createdAt(rfq.getCreatedAt())
            .updatedAt(rfq.getUpdatedAt())
            .quote(quote != null ? toQuoteDTO(quote) : null)
            .build();
    }

    private RfqQuoteDTO toQuoteDTO(RfqQuote quote) {
        return RfqQuoteDTO.builder()
            .id(quote.getId())
            .rfqId(quote.getRfqId())
            .supplierNo(quote.getSupplierNo())
            .unitPrice(quote.getUnitPrice())
            .totalAmount(quote.getTotalAmount())
            .currency(quote.getCurrency())
            .deliveryDays(quote.getDeliveryDays())
            .validUntil(quote.getValidUntil())
            .paymentTerms(quote.getPaymentTerms())
            .supplierRemark(quote.getSupplierRemark())
            .createdAt(quote.getCreatedAt())
            .build();
    }
}
