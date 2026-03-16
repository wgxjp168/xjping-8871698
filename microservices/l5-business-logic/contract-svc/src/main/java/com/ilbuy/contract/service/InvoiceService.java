package com.ilbuy.contract.service;

import com.ilbuy.contract.model.dto.*;
import com.ilbuy.contract.model.entity.Contract;
import com.ilbuy.contract.model.entity.Invoice;
import com.ilbuy.contract.model.enums.InvoiceStatus;
import com.ilbuy.contract.repository.ContractRepository;
import com.ilbuy.contract.repository.InvoiceRepository;
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
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Random;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class InvoiceService {

    private final InvoiceRepository invoiceRepository;
    private final ContractRepository contractRepository;

    private static final Random RANDOM = new Random();
    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMdd");

    // Default VAT rate 13%
    private static final BigDecimal DEFAULT_TAX_RATE = new BigDecimal("0.13");

    @Transactional
    public InvoiceDTO createInvoice(Long userId, CreateInvoiceRequest request) {
        Contract contract = contractRepository.findById(request.getContractId())
            .orElseThrow(() -> new IllegalArgumentException("合同不存在: " + request.getContractId()));

        BigDecimal amount = contract.getTotalAmount();
        BigDecimal taxAmount = amount.multiply(DEFAULT_TAX_RATE).setScale(2, RoundingMode.HALF_UP);

        Invoice invoice = Invoice.builder()
            .contractId(request.getContractId())
            .userId(userId)
            .type(request.getType())
            .amount(amount)
            .taxRate(DEFAULT_TAX_RATE)
            .taxAmount(taxAmount)
            .invoiceTitle(request.getInvoiceTitle())
            .taxpayerId(request.getTaxpayerId())
            .bankAccount(request.getBankAccount())
            .bankName(request.getBankName())
            .companyAddress(request.getCompanyAddress())
            .status(InvoiceStatus.PENDING)
            .mailingAddress(request.getMailingAddress())
            .build();

        invoice = invoiceRepository.save(invoice);
        log.info("Invoice request created for contractId={}, userId={}", request.getContractId(), userId);
        return toDTO(invoice);
    }

    @Transactional(readOnly = true)
    public PageResult<InvoiceDTO> listInvoices(Long userId, int page, int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<Invoice> invoicePage = invoiceRepository.findByUserId(userId, pageable);

        List<InvoiceDTO> content = invoicePage.getContent().stream()
            .map(this::toDTO)
            .collect(Collectors.toList());

        return PageResult.<InvoiceDTO>builder()
            .content(content)
            .page(page)
            .size(size)
            .totalElements(invoicePage.getTotalElements())
            .totalPages(invoicePage.getTotalPages())
            .build();
    }

    @Transactional(readOnly = true)
    public InvoiceDTO getInvoiceDetail(String invoiceNo) {
        Invoice invoice = findByInvoiceNo(invoiceNo);
        return toDTO(invoice);
    }

    @Transactional
    public InvoiceDTO issueInvoice(String invoiceNo) {
        Invoice invoice = findByInvoiceNo(invoiceNo);

        if (invoice.getStatus() != InvoiceStatus.PENDING) {
            throw new IllegalStateException("发票状态不允许开具，当前状态: " + invoice.getStatus());
        }

        String generatedInvoiceNo = generateInvoiceNo();
        invoice.setInvoiceNo(generatedInvoiceNo);
        invoice.setStatus(InvoiceStatus.ISSUED);
        invoice.setIssueDate(LocalDate.now());

        invoice = invoiceRepository.save(invoice);
        log.info("Invoice issued: {}", generatedInvoiceNo);
        return toDTO(invoice);
    }

    @Transactional
    public InvoiceDTO mailInvoice(String invoiceNo, String trackingNo) {
        Invoice invoice = findByInvoiceNo(invoiceNo);

        if (invoice.getStatus() != InvoiceStatus.ISSUED) {
            throw new IllegalStateException("只有已开具的发票才能标记为已邮寄，当前状态: " + invoice.getStatus());
        }

        invoice.setTrackingNo(trackingNo);
        invoice.setStatus(InvoiceStatus.MAILED);

        invoice = invoiceRepository.save(invoice);
        log.info("Invoice {} marked as mailed with tracking={}", invoiceNo, trackingNo);
        return toDTO(invoice);
    }

    @Transactional
    public InvoiceDTO voidInvoice(String invoiceNo) {
        Invoice invoice = findByInvoiceNo(invoiceNo);

        if (invoice.getStatus() == InvoiceStatus.VOID) {
            throw new IllegalStateException("发票已作废");
        }

        invoice.setStatus(InvoiceStatus.VOID);
        invoice = invoiceRepository.save(invoice);
        log.info("Invoice {} voided", invoiceNo);
        return toDTO(invoice);
    }

    private Invoice findByInvoiceNo(String invoiceNo) {
        return invoiceRepository.findByInvoiceNo(invoiceNo)
            .orElseThrow(() -> new IllegalArgumentException("发票不存在: " + invoiceNo));
    }

    private String generateInvoiceNo() {
        String date = LocalDateTime.now().format(DATE_FORMATTER);
        int random = RANDOM.nextInt(100_000_000);
        String invoiceNo = String.format("INV%s%08d", date, random);
        // Ensure uniqueness
        while (invoiceRepository.existsByInvoiceNo(invoiceNo)) {
            random = RANDOM.nextInt(100_000_000);
            invoiceNo = String.format("INV%s%08d", date, random);
        }
        return invoiceNo;
    }

    private InvoiceDTO toDTO(Invoice invoice) {
        return InvoiceDTO.builder()
            .id(invoice.getId())
            .invoiceNo(invoice.getInvoiceNo())
            .contractId(invoice.getContractId())
            .userId(invoice.getUserId())
            .type(invoice.getType())
            .amount(invoice.getAmount())
            .taxRate(invoice.getTaxRate())
            .taxAmount(invoice.getTaxAmount())
            .invoiceTitle(invoice.getInvoiceTitle())
            .taxpayerId(invoice.getTaxpayerId())
            .bankAccount(invoice.getBankAccount())
            .bankName(invoice.getBankName())
            .companyAddress(invoice.getCompanyAddress())
            .status(invoice.getStatus())
            .issueDate(invoice.getIssueDate())
            .mailingAddress(invoice.getMailingAddress())
            .trackingNo(invoice.getTrackingNo())
            .createdAt(invoice.getCreatedAt())
            .build();
    }
}
