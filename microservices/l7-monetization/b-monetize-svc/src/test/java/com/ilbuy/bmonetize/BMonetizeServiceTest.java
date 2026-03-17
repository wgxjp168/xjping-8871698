package com.ilbuy.bmonetize;

import com.ilbuy.bmonetize.domain.BMonetizeOrder;
import com.ilbuy.bmonetize.domain.BMonetizeOrder.*;
import com.ilbuy.bmonetize.domain.BSaasContract;
import com.ilbuy.bmonetize.dto.CreateBOrderRequest;
import com.ilbuy.bmonetize.dto.BOrderResponse;
import com.ilbuy.bmonetize.repository.*;
import com.ilbuy.bmonetize.service.BMonetizeService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.*;
import org.springframework.web.client.RestTemplate;
import java.math.BigDecimal;
import java.util.*;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class BMonetizeServiceTest {

    @Mock BMonetizeOrderRepository orderRepository;
    @Mock BSaasContractRepository contractRepository;
    @Mock RestTemplate restTemplate;
    @InjectMocks BMonetizeService bMonetizeService;

    @Test
    void createSaasOrder_success() {
        CreateBOrderRequest req = new CreateBOrderRequest();
        req.setCorpId(500L); req.setContactUserId(100L);
        req.setProductType(ProductType.SAAS_ANNUAL);
        req.setProductId("ENTERPRISE"); req.setAmount(new BigDecimal("9800.00"));
        req.setPaymentChannel("ALIPAY");

        when(orderRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));
        when(restTemplate.postForEntity(anyString(), any(), eq(Map.class)))
            .thenReturn(ResponseEntity.ok(Map.of("paymentNo", "PAY-B-001")));

        BOrderResponse resp = bMonetizeService.createOrder(req);
        assertThat(resp.getProductType()).isEqualTo(ProductType.SAAS_ANNUAL);
        assertThat(resp.getAmount()).isEqualByComparingTo("9800.00");
        assertThat(resp.getStatus()).isEqualTo(OrderStatus.PENDING_PAYMENT);
    }

    @Test
    void confirmPayment_activatesSaasContract() {
        BMonetizeOrder order = BMonetizeOrder.builder()
            .orderNo("BO-001").corpId(500L).contactUserId(100L)
            .productType(ProductType.SAAS_ANNUAL).productId("ENTERPRISE")
            .amount(new BigDecimal("9800.00")).status(OrderStatus.PENDING_PAYMENT).build();
        when(orderRepository.findByOrderNo("BO-001")).thenReturn(Optional.of(order));
        when(orderRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));
        when(contractRepository.findByCorpIdAndStatus(500L, BSaasContract.ContractStatus.ACTIVE))
            .thenReturn(Optional.empty());
        when(contractRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        bMonetizeService.confirmPayment("PAY-001", "BO-001");

        assertThat(order.getStatus()).isEqualTo(OrderStatus.PAID);
        verify(contractRepository).save(argThat(c -> c.getStatus() == BSaasContract.ContractStatus.ACTIVE));
    }

    @Test
    void confirmPayment_idempotent() {
        BMonetizeOrder order = BMonetizeOrder.builder()
            .orderNo("BO-002").status(OrderStatus.PAID).build();
        when(orderRepository.findByOrderNo("BO-002")).thenReturn(Optional.of(order));
        bMonetizeService.confirmPayment("PAY-002", "BO-002");
        verify(orderRepository, never()).save(any());
    }
}
