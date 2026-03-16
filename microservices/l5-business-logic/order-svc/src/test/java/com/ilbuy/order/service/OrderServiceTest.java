package com.ilbuy.order.service;

import com.ilbuy.order.model.dto.CreateOrderRequest;
import com.ilbuy.order.model.dto.OrderDTO;
import com.ilbuy.order.model.entity.Order;
import com.ilbuy.order.model.entity.OrderItem;
import com.ilbuy.order.model.enums.OrderStatus;
import com.ilbuy.order.model.enums.PaymentMethod;
import com.ilbuy.order.mq.OrderEventPublisher;
import com.ilbuy.order.repository.OrderRepository;
import com.ilbuy.order.util.OrderNoGenerator;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @Mock OrderRepository     orderRepository;
    @Mock OrderEventPublisher eventPublisher;

    OrderNoGenerator orderNoGenerator = new OrderNoGenerator();
    OrderService     orderService;

    @BeforeEach
    void setUp() {
        orderService = new OrderService(orderRepository, orderNoGenerator, eventPublisher);
    }

    private CreateOrderRequest buildRequest() {
        CreateOrderRequest req = new CreateOrderRequest();
        req.setPaymentMethod(PaymentMethod.ALIPAY);
        req.setShippingName("张三");
        req.setShippingPhone("13800138000");
        req.setShippingAddress("天安门广场1号");
        req.setShippingCity("北京");
        req.setShippingProvince("北京");

        CreateOrderRequest.OrderItemRequest item = new CreateOrderRequest.OrderItemRequest();
        item.setCanonicalId("canon-001");
        item.setPlatform("jd");
        item.setProductTitle("iPhone 15 Pro");
        item.setUnitPrice(new BigDecimal("7999.00"));
        item.setQuantity(1);
        req.setItems(List.of(item));
        return req;
    }

    private Order buildSavedOrder(Long id, String orderNo, Long userId) {
        Order order = Order.builder()
            .id(id).orderNo(orderNo).userId(userId)
            .status(OrderStatus.PENDING)
            .totalAmount(new BigDecimal("7999.00"))
            .discountAmount(BigDecimal.ZERO)
            .finalAmount(new BigDecimal("7999.00"))
            .paymentMethod(PaymentMethod.ALIPAY)
            .shippingName("张三").shippingPhone("13800138000")
            .shippingAddress("天安门广场1号").shippingCity("北京").shippingProvince("北京")
            .items(new ArrayList<>())
            .createdAt(Instant.now())
            .build();

        OrderItem item = OrderItem.builder()
            .id(1L).order(order).canonicalId("canon-001").platform("jd")
            .productTitle("iPhone 15 Pro")
            .unitPrice(new BigDecimal("7999.00")).quantity(1)
            .subtotal(new BigDecimal("7999.00"))
            .build();
        order.getItems().add(item);
        return order;
    }

    @Test
    void createOrder_success() {
        Order saved = buildSavedOrder(1L, "ORD-20240316-00000001", 42L);
        when(orderRepository.save(any(Order.class))).thenReturn(saved);

        OrderDTO dto = orderService.createOrder(42L, buildRequest());

        assertThat(dto.getOrderNo()).isEqualTo("ORD-20240316-00000001");
        assertThat(dto.getStatus()).isEqualTo(OrderStatus.PENDING);
        assertThat(dto.getFinalAmount()).isEqualByComparingTo("7999.00");
        assertThat(dto.getItems()).hasSize(1);

        verify(eventPublisher).publishOrderCreated(any());
    }

    @Test
    void payOrder_success() {
        Order pending = buildSavedOrder(1L, "ORD-001", 42L);
        Order paid = buildSavedOrder(1L, "ORD-001", 42L);
        paid.setStatus(OrderStatus.PAID);
        paid.setPaidAt(Instant.now());

        when(orderRepository.findByOrderNo("ORD-001")).thenReturn(Optional.of(pending));
        when(orderRepository.save(any(Order.class))).thenReturn(paid);

        OrderDTO dto = orderService.payOrder(42L, "ORD-001");

        assertThat(dto.getStatus()).isEqualTo(OrderStatus.PAID);
        verify(eventPublisher).publishOrderPaid(any());
    }

    @Test
    void payOrder_wrongOwner_throws() {
        Order order = buildSavedOrder(1L, "ORD-001", 42L);
        when(orderRepository.findByOrderNo("ORD-001")).thenReturn(Optional.of(order));

        assertThatThrownBy(() -> orderService.payOrder(99L, "ORD-001"))
            .isInstanceOf(IllegalArgumentException.class)
            .hasMessageContaining("无权访问");
    }

    @Test
    void cancelOrder_alreadyShipped_throws() {
        Order shipped = buildSavedOrder(1L, "ORD-001", 42L);
        shipped.setStatus(OrderStatus.SHIPPED);

        when(orderRepository.findByOrderNo("ORD-001")).thenReturn(Optional.of(shipped));

        assertThatThrownBy(() -> orderService.cancelOrder(42L, "ORD-001", "change mind"))
            .isInstanceOf(IllegalStateException.class);
    }

    @Test
    void getOrder_notFound_throws() {
        when(orderRepository.findByOrderNo("NONEXIST")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> orderService.getOrder(1L, "NONEXIST"))
            .isInstanceOf(IllegalArgumentException.class)
            .hasMessageContaining("订单不存在");
    }
}
