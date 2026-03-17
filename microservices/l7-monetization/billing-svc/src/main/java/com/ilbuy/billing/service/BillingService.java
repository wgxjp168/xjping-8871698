package com.ilbuy.billing.service;

import com.ilbuy.billing.domain.Invoice;
import com.ilbuy.billing.domain.Invoice.InvoiceStatus;
import com.ilbuy.billing.domain.RefundRecord;
import com.ilbuy.billing.domain.RefundRecord.RefundStatus;
import com.ilbuy.billing.domain.RevenueRecord;
import com.ilbuy.billing.dto.CreateRefundRequest;
import com.ilbuy.billing.dto.InvoiceResponse;
import com.ilbuy.billing.dto.RefundResponse;
import com.ilbuy.billing.repository.InvoiceRepository;
import com.ilbuy.billing.repository.RefundRecordRepository;
import com.ilbuy.billing.repository.RevenueRecordRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.YearMonth;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
@Transactional
public class BillingService {

    private final InvoiceRepository invoiceRepository;
    private final RefundRecordRepository refundRecordRepository;
    private final RevenueRecordRepository revenueRecordRepository;
    private final RestTemplate restTemplate;

    @Value("${ilbuy.gateway.url:http://monetize-gateway-svc:8071}")
    private String gatewayUrl;

    /**
     * Issue an invoice for a given order.
     */
    public InvoiceResponse issueInvoice(String orderNo, String orderType,
                                        Long userId, Long corpId, BigDecimal amount) {
        String invoiceNo = "INV-" + UUID.randomUUID().toString().replace("-", "").substring(0, 16).toUpperCase();
        Invoice invoice = Invoice.builder()
                .invoiceNo(invoiceNo)
                .orderNo(orderNo)
                .orderType(orderType)
                .userId(userId)
                .corpId(corpId)
                .amount(amount)
                .currency("CNY")
                .status(InvoiceStatus.ISSUED)
                .issuedAt(LocalDateTime.now())
                .build();
        Invoice saved = invoiceRepository.save(invoice);
        log.info("Invoice issued: {} for order: {}", invoiceNo, orderNo);
        return toInvoiceResponse(saved);
    }

    /**
     * Create a refund record and call the gateway to process it.
     */
    public RefundResponse createRefund(CreateRefundRequest request) {
        String refundNo = "REF-" + UUID.randomUUID().toString().replace("-", "").substring(0, 16).toUpperCase();
        RefundRecord record = RefundRecord.builder()
                .refundNo(refundNo)
                .originalOrderNo(request.getOriginalOrderNo())
                .paymentNo(request.getPaymentNo())
                .userId(request.getUserId())
                .corpId(request.getCorpId())
                .refundAmount(request.getRefundAmount())
                .reason(request.getReason())
                .status(RefundStatus.PENDING)
                .build();
        RefundRecord saved = refundRecordRepository.save(record);
        log.info("Refund record created: {} for order: {}", refundNo, request.getOriginalOrderNo());

        // Call gateway to initiate the refund
        try {
            String url = gatewayUrl + "/api/v1/refunds";
            ResponseEntity<Void> response = restTemplate.postForEntity(url, request, Void.class);
            if (response.getStatusCode().is2xxSuccessful()) {
                saved.setStatus(RefundStatus.PROCESSING);
                saved = refundRecordRepository.save(saved);
                log.info("Refund {} submitted to gateway, status PROCESSING", refundNo);
            }
        } catch (Exception e) {
            log.warn("Gateway call failed for refund {}: {}. Staying PENDING.", refundNo, e.getMessage());
        }

        return toRefundResponse(saved);
    }

    /**
     * Retrieve an invoice by its invoice number.
     */
    @Transactional(readOnly = true)
    public InvoiceResponse getInvoice(String invoiceNo) {
        Invoice invoice = invoiceRepository.findByInvoiceNo(invoiceNo)
                .orElseThrow(() -> new IllegalArgumentException("Invoice not found: " + invoiceNo));
        return toInvoiceResponse(invoice);
    }

    /**
     * Retrieve a refund record by its refund number.
     */
    @Transactional(readOnly = true)
    public RefundResponse getRefund(String refundNo) {
        RefundRecord record = refundRecordRepository.findByRefundNo(refundNo)
                .orElseThrow(() -> new IllegalArgumentException("Refund not found: " + refundNo));
        return toRefundResponse(record);
    }

    /**
     * Handle payment success event — auto-issue invoice.
     */
    public InvoiceResponse handlePaymentSuccess(String paymentNo, String bizOrderNo, String orderType,
                                                Long userId, Long corpId, BigDecimal amount) {
        log.info("Handling payment success: paymentNo={}, bizOrderNo={}, orderType={}", paymentNo, bizOrderNo, orderType);
        return issueInvoice(bizOrderNo, orderType, userId, corpId, amount);
    }

    /**
     * Monthly scheduled job — aggregate revenue for the prior calendar month.
     * Runs at 03:00 on the 1st of every month.
     */
    @Scheduled(cron = "0 0 3 1 * *")
    public void generateMonthlyRevenue() {
        YearMonth priorMonth = YearMonth.now().minusMonths(1);
        String period = priorMonth.format(DateTimeFormatter.ofPattern("yyyy-MM"));
        log.info("Generating monthly revenue report for period: {}", period);

        LocalDateTime start = priorMonth.atDay(1).atStartOfDay();
        LocalDateTime end = priorMonth.atEndOfMonth().atTime(23, 59, 59);

        List<Invoice> invoices = invoiceRepository.findAll().stream()
                .filter(inv -> inv.getIssuedAt() != null
                        && !inv.getIssuedAt().isBefore(start)
                        && !inv.getIssuedAt().isAfter(end)
                        && inv.getStatus() == InvoiceStatus.ISSUED)
                .collect(Collectors.toList());

        Map<String, List<Invoice>> byType = invoices.stream()
                .collect(Collectors.groupingBy(Invoice::getOrderType));

        for (Map.Entry<String, List<Invoice>> entry : byType.entrySet()) {
            String orderType = entry.getKey();
            List<Invoice> group = entry.getValue();
            BigDecimal totalRevenue = group.stream()
                    .map(Invoice::getAmount)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);

            // Sum refunds for this order type in the period
            List<RefundRecord> refunds = refundRecordRepository.findAll().stream()
                    .filter(r -> r.getStatus() == RefundRecord.RefundStatus.COMPLETED
                            && r.getCreatedAt() != null
                            && !r.getCreatedAt().isBefore(start)
                            && !r.getCreatedAt().isAfter(end))
                    .collect(Collectors.toList());
            BigDecimal refundAmount = refunds.stream()
                    .map(RefundRecord::getRefundAmount)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);

            BigDecimal netRevenue = totalRevenue.subtract(refundAmount);

            RevenueRecord record = RevenueRecord.builder()
                    .period(period)
                    .orderType(orderType)
                    .orderCount(group.size())
                    .totalRevenue(totalRevenue)
                    .refundAmount(refundAmount)
                    .netRevenue(netRevenue)
                    .build();
            revenueRecordRepository.save(record);
            log.info("Revenue record saved: period={}, orderType={}, net={}", period, orderType, netRevenue);
        }
    }

    // ---- Mappers ----

    private InvoiceResponse toInvoiceResponse(Invoice inv) {
        return InvoiceResponse.builder()
                .invoiceNo(inv.getInvoiceNo())
                .userId(inv.getUserId())
                .corpId(inv.getCorpId())
                .orderNo(inv.getOrderNo())
                .orderType(inv.getOrderType())
                .amount(inv.getAmount())
                .currency(inv.getCurrency())
                .status(inv.getStatus())
                .issuedAt(inv.getIssuedAt())
                .createdAt(inv.getCreatedAt())
                .build();
    }

    private RefundResponse toRefundResponse(RefundRecord r) {
        return RefundResponse.builder()
                .refundNo(r.getRefundNo())
                .originalOrderNo(r.getOriginalOrderNo())
                .paymentNo(r.getPaymentNo())
                .refundAmount(r.getRefundAmount())
                .status(r.getStatus())
                .processedAt(r.getProcessedAt())
                .createdAt(r.getCreatedAt())
                .build();
    }
}
