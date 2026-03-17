package com.ilbuy.billing;

import com.ilbuy.billing.domain.Invoice;
import com.ilbuy.billing.domain.Invoice.InvoiceStatus;
import com.ilbuy.billing.domain.RefundRecord;
import com.ilbuy.billing.domain.RefundRecord.RefundStatus;
import com.ilbuy.billing.dto.CreateRefundRequest;
import com.ilbuy.billing.dto.InvoiceResponse;
import com.ilbuy.billing.dto.RefundResponse;
import com.ilbuy.billing.repository.InvoiceRepository;
import com.ilbuy.billing.repository.RefundRecordRepository;
import com.ilbuy.billing.repository.RevenueRecordRepository;
import com.ilbuy.billing.service.BillingService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.ResponseEntity;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.time.LocalDateTime;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class BillingServiceTest {

    @Mock
    private InvoiceRepository invoiceRepository;

    @Mock
    private RefundRecordRepository refundRecordRepository;

    @Mock
    private RevenueRecordRepository revenueRecordRepository;

    @Mock
    private RestTemplate restTemplate;

    @InjectMocks
    private BillingService billingService;

    // ---- Test 1 ----

    @Test
    void issueInvoice_createsIssuedInvoice() {
        // Arrange: mock save to return the argument passed in
        when(invoiceRepository.save(any(Invoice.class))).thenAnswer(invocation -> {
            Invoice inv = invocation.getArgument(0);
            inv.setId(1L);
            inv.setCreatedAt(LocalDateTime.now());
            return inv;
        });

        // Act
        InvoiceResponse response = billingService.issueInvoice(
                "ORD-001", "C_ORDER", 42L, null, new BigDecimal("99.00"));

        // Assert
        assertThat(response.getInvoiceNo()).startsWith("INV-");
        assertThat(response.getStatus()).isEqualTo(InvoiceStatus.ISSUED);
        assertThat(response.getOrderNo()).isEqualTo("ORD-001");
        assertThat(response.getOrderType()).isEqualTo("C_ORDER");
        assertThat(response.getUserId()).isEqualTo(42L);
        assertThat(response.getAmount()).isEqualByComparingTo(new BigDecimal("99.00"));
        verify(invoiceRepository, times(1)).save(any(Invoice.class));
    }

    // ---- Test 2 ----

    @Test
    void createRefund_callsGatewayAndSavesRecord() {
        // Arrange: save returns the argument
        when(refundRecordRepository.save(any(RefundRecord.class))).thenAnswer(invocation -> {
            RefundRecord r = invocation.getArgument(0);
            r.setId(1L);
            r.setCreatedAt(LocalDateTime.now());
            return r;
        });
        // Mock gateway being down — restTemplate throws exception
        when(restTemplate.postForEntity(anyString(), any(), eq(Void.class)))
                .thenThrow(new RuntimeException("Gateway connection refused"));

        CreateRefundRequest request = new CreateRefundRequest();
        request.setOriginalOrderNo("ORD-001");
        request.setPaymentNo("PAY-001");
        request.setUserId(42L);
        request.setRefundAmount(new BigDecimal("50.00"));
        request.setReason("Customer request");

        // Act
        RefundResponse response = billingService.createRefund(request);

        // Assert: refund saved with PENDING status (gateway failed, so stays PENDING)
        assertThat(response.getRefundNo()).startsWith("REF-");
        assertThat(response.getStatus()).isEqualTo(RefundStatus.PENDING);
        assertThat(response.getOriginalOrderNo()).isEqualTo("ORD-001");
        // save called at least once (initial PENDING save)
        verify(refundRecordRepository, atLeastOnce()).save(any(RefundRecord.class));
    }

    // ---- Test 3 ----

    @Test
    void getInvoice_returnsInvoice() {
        // Arrange
        Invoice invoice = Invoice.builder()
                .id(1L)
                .invoiceNo("INV-ABCDEF1234567890")
                .orderNo("ORD-999")
                .orderType("B_ORDER")
                .userId(10L)
                .amount(new BigDecimal("500.00"))
                .currency("CNY")
                .status(InvoiceStatus.ISSUED)
                .issuedAt(LocalDateTime.now())
                .createdAt(LocalDateTime.now())
                .build();

        when(invoiceRepository.findByInvoiceNo("INV-ABCDEF1234567890"))
                .thenReturn(java.util.Optional.of(invoice));

        // Act
        InvoiceResponse response = billingService.getInvoice("INV-ABCDEF1234567890");

        // Assert
        assertThat(response.getInvoiceNo()).isEqualTo("INV-ABCDEF1234567890");
        assertThat(response.getOrderNo()).isEqualTo("ORD-999");
        assertThat(response.getOrderType()).isEqualTo("B_ORDER");
        assertThat(response.getUserId()).isEqualTo(10L);
        assertThat(response.getAmount()).isEqualByComparingTo(new BigDecimal("500.00"));
        assertThat(response.getStatus()).isEqualTo(InvoiceStatus.ISSUED);
    }

    // ---- Test 4 ----

    @Test
    void handlePaymentSuccess_autoIssuedInvoice() {
        // Arrange: mock save to return the argument
        when(invoiceRepository.save(any(Invoice.class))).thenAnswer(invocation -> {
            Invoice inv = invocation.getArgument(0);
            inv.setId(2L);
            inv.setCreatedAt(LocalDateTime.now());
            return inv;
        });

        // Act
        InvoiceResponse response = billingService.handlePaymentSuccess(
                "PAY-XYZ", "ORD-DATA-001", "DATA_ORDER", null, 77L, new BigDecimal("200.00"));

        // Assert: invoice created with correct orderType
        assertThat(response.getOrderType()).isEqualTo("DATA_ORDER");
        assertThat(response.getOrderNo()).isEqualTo("ORD-DATA-001");
        assertThat(response.getStatus()).isEqualTo(InvoiceStatus.ISSUED);
        assertThat(response.getCorpId()).isEqualTo(77L);
        verify(invoiceRepository, times(1)).save(any(Invoice.class));
    }
}
