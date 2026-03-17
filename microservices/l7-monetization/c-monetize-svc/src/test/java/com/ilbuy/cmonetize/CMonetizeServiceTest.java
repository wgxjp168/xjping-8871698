package com.ilbuy.cmonetize;

import com.ilbuy.cmonetize.domain.CMonetizeOrder;
import com.ilbuy.cmonetize.domain.CMonetizeOrder.*;
import com.ilbuy.cmonetize.domain.MembershipPlan;
import com.ilbuy.cmonetize.dto.CreateOrderRequest;
import com.ilbuy.cmonetize.dto.OrderResponse;
import com.ilbuy.cmonetize.repository.CMonetizeOrderRepository;
import com.ilbuy.cmonetize.repository.MembershipPlanRepository;
import com.ilbuy.cmonetize.service.CMonetizeService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.*;
import org.springframework.web.client.RestTemplate;
import java.math.BigDecimal;
import java.util.Map;
import java.util.Optional;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class CMonetizeServiceTest {

    @Mock CMonetizeOrderRepository orderRepository;
    @Mock MembershipPlanRepository planRepository;
    @Mock RestTemplate restTemplate;

    @InjectMocks CMonetizeService cMonetizeService;

    @Test
    void createSingleReportOrder_success() {
        CreateOrderRequest req = new CreateOrderRequest();
        req.setUserId(100L);
        req.setProductType(ProductType.SINGLE_REPORT);
        req.setProductId("RPT-2024-001");
        req.setPaymentChannel("WECHAT");
        req.setChannelUserId("openid_test");

        when(orderRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));
        when(restTemplate.postForEntity(anyString(), any(), eq(Map.class)))
            .thenReturn(ResponseEntity.ok(Map.of("paymentNo", "PAY-001", "channelPayParams", Map.of("prepay_id", "wx123"))));

        OrderResponse resp = cMonetizeService.createOrder(req);

        assertThat(resp.getProductType()).isEqualTo(ProductType.SINGLE_REPORT);
        assertThat(resp.getAmount()).isEqualByComparingTo("99.00");
        assertThat(resp.getStatus()).isEqualTo(OrderStatus.PENDING_PAYMENT);
        verify(orderRepository, times(2)).save(any());
    }

    @Test
    void createMembershipOrder_usesPlanPrice() {
        MembershipPlan plan = MembershipPlan.builder()
            .planCode("ANNUAL").name("年度会员").durationMonths(12)
            .price(new BigDecimal("599.00")).isActive(true).build();
        when(planRepository.findByPlanCode("ANNUAL")).thenReturn(Optional.of(plan));
        when(orderRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));
        when(restTemplate.postForEntity(anyString(), any(), eq(Map.class)))
            .thenReturn(ResponseEntity.ok(Map.of("paymentNo", "PAY-002")));

        CreateOrderRequest req = new CreateOrderRequest();
        req.setUserId(200L);
        req.setProductType(ProductType.MEMBERSHIP);
        req.setProductId("ANNUAL");
        req.setPaymentChannel("ALIPAY");

        OrderResponse resp = cMonetizeService.createOrder(req);
        assertThat(resp.getAmount()).isEqualByComparingTo("599.00");
    }

    @Test
    void confirmPayment_updatesOrderStatus() {
        CMonetizeOrder order = CMonetizeOrder.builder()
            .orderNo("CO-001").userId(100L)
            .productType(ProductType.SINGLE_REPORT).productId("RPT-001")
            .amount(new BigDecimal("99.00")).status(OrderStatus.PENDING_PAYMENT).build();
        when(orderRepository.findByOrderNo("CO-001")).thenReturn(Optional.of(order));
        when(orderRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        cMonetizeService.confirmPayment("PAY-001", "CO-001");

        assertThat(order.getStatus()).isEqualTo(OrderStatus.PAID);
        assertThat(order.getPaidAt()).isNotNull();
    }

    @Test
    void confirmPayment_idempotent_whenAlreadyPaid() {
        CMonetizeOrder order = CMonetizeOrder.builder()
            .orderNo("CO-002").status(OrderStatus.PAID).build();
        when(orderRepository.findByOrderNo("CO-002")).thenReturn(Optional.of(order));

        cMonetizeService.confirmPayment("PAY-002", "CO-002");
        verify(orderRepository, never()).save(any());
    }
}
