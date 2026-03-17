package com.ilbuy.datamonetize;

import com.ilbuy.datamonetize.domain.DataOrder;
import com.ilbuy.datamonetize.domain.DataOrder.OrderStatus;
import com.ilbuy.datamonetize.domain.DataProduct;
import com.ilbuy.datamonetize.dto.CreateDataOrderRequest;
import com.ilbuy.datamonetize.dto.DataOrderResponse;
import com.ilbuy.datamonetize.repository.DataOrderRepository;
import com.ilbuy.datamonetize.repository.DataProductRepository;
import com.ilbuy.datamonetize.service.DataMonetizeService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class DataMonetizeServiceTest {

    @Mock
    DataOrderRepository orderRepository;

    @Mock
    DataProductRepository productRepository;

    @Mock
    RestTemplate restTemplate;

    @InjectMocks
    DataMonetizeService dataMonetizeService;

    @Test
    void createOrder_savesOrderWithCorrectAmount() {
        DataProduct product = DataProduct.builder()
            .productCode("REPORT-001")
            .name("市场分析报告")
            .category("MARKET_REPORT")
            .unitPrice(new BigDecimal("299.00"))
            .enabled(true)
            .build();

        when(productRepository.findByProductCodeAndEnabled("REPORT-001", true))
            .thenReturn(Optional.of(product));
        when(orderRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));
        when(restTemplate.postForEntity(anyString(), any(), eq(java.util.Map.class)))
            .thenThrow(new RuntimeException("gateway unavailable"));

        CreateDataOrderRequest req = new CreateDataOrderRequest();
        req.setUserId(100L);
        req.setProductCode("REPORT-001");
        req.setQuantity(2);
        req.setPaymentChannel("ALIPAY");

        DataOrderResponse resp = dataMonetizeService.createOrder(req);

        assertThat(resp.getOrderNo()).startsWith("DO-");
        assertThat(resp.getStatus()).isEqualTo(OrderStatus.PENDING_PAYMENT);
        assertThat(resp.getTotalAmount()).isEqualByComparingTo("598.00");
    }

    @Test
    void confirmPayment_updatesOrderToPaid() {
        DataOrder order = DataOrder.builder()
            .orderNo("DO-TESTORDER001")
            .userId(100L)
            .productCode("REPORT-001")
            .productName("市场分析报告")
            .unitPrice(new BigDecimal("299.00"))
            .quantity(1)
            .totalAmount(new BigDecimal("299.00"))
            .status(OrderStatus.PENDING_PAYMENT)
            .build();

        when(orderRepository.findByOrderNo("DO-TESTORDER001")).thenReturn(Optional.of(order));
        when(orderRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));
        when(productRepository.findByProductCodeAndEnabled("REPORT-001", true))
            .thenReturn(Optional.empty());

        dataMonetizeService.confirmPayment("PAY-DATA-001", "DO-TESTORDER001");

        assertThat(order.getStatus()).isEqualTo(OrderStatus.PAID);
        assertThat(order.getPaymentNo()).isEqualTo("PAY-DATA-001");
        assertThat(order.getPaidAt()).isNotNull();
    }

    @Test
    void confirmPayment_skipsDuplicate() {
        DataOrder order = DataOrder.builder()
            .orderNo("DO-ALREADY-PAID")
            .userId(200L)
            .productCode("API-001")
            .productName("数据API接入")
            .unitPrice(new BigDecimal("99.00"))
            .quantity(1)
            .totalAmount(new BigDecimal("99.00"))
            .status(OrderStatus.PAID)
            .build();

        when(orderRepository.findByOrderNo("DO-ALREADY-PAID")).thenReturn(Optional.of(order));

        dataMonetizeService.confirmPayment("PAY-DATA-002", "DO-ALREADY-PAID");

        verify(orderRepository, never()).save(any());
    }

    @Test
    void getAvailableProducts_returnsOnlyEnabled() {
        DataProduct p1 = DataProduct.builder()
            .productCode("REPORT-001")
            .name("市场分析报告")
            .category("MARKET_REPORT")
            .unitPrice(new BigDecimal("299.00"))
            .enabled(true)
            .build();
        DataProduct p2 = DataProduct.builder()
            .productCode("API-001")
            .name("数据API接入")
            .category("API_DATA")
            .unitPrice(new BigDecimal("99.00"))
            .enabled(true)
            .build();

        when(productRepository.findAllByEnabledTrue()).thenReturn(List.of(p1, p2));

        List<DataProduct> products = dataMonetizeService.getAvailableProducts();

        assertThat(products).hasSize(2);
        verify(productRepository).findAllByEnabledTrue();
    }
}
