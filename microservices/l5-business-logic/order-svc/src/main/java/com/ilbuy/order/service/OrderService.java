package com.ilbuy.order.service;

import com.ilbuy.order.model.dto.*;
import com.ilbuy.order.model.entity.Order;
import com.ilbuy.order.model.entity.OrderItem;
import com.ilbuy.order.model.enums.OrderScene;
import com.ilbuy.order.model.enums.OrderStatus;
import com.ilbuy.order.mq.OrderEventPublisher;
import com.ilbuy.order.repository.OrderRepository;
import com.ilbuy.order.util.OrderNoGenerator;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class OrderService {

    private final OrderRepository     orderRepository;
    private final OrderNoGenerator    orderNoGenerator;
    private final OrderEventPublisher eventPublisher;

    // ── 创建订单 ─────────────────────────────────────────────────

    @Transactional
    public OrderDTO createOrder(Long userId, CreateOrderRequest request) {
        // 计算总金额
        BigDecimal total = request.getItems().stream()
            .map(i -> i.getUnitPrice().multiply(BigDecimal.valueOf(i.getQuantity())))
            .reduce(BigDecimal.ZERO, BigDecimal::add);

        // ── B2B/B2C 场景校验 ──────────────────────────────────────
        OrderScene scene = request.getScene() != null ? request.getScene() : OrderScene.B2C;
        if (scene == OrderScene.B2B) {
            // B2B：开具专票时 invoiceTitle 和 taxpayerId 必填
            if (Boolean.TRUE.equals(request.getInvoiceRequired())) {
                if (request.getInvoiceTitle() == null || request.getInvoiceTitle().isBlank()) {
                    throw new IllegalArgumentException("B2B 开票申请需提供开票抬头");
                }
                if (request.getTaxpayerId() == null || request.getTaxpayerId().isBlank()) {
                    throw new IllegalArgumentException("B2B 开票申请需提供纳税人识别号");
                }
            }
            log.info("B2B order: userId={} supplierNo={} contractNo={} invoiceRequired={}",
                    userId, request.getSupplierNo(), request.getContractNo(), request.getInvoiceRequired());
        }

        // ── B2C 优惠券折扣（mock：固定减 10 元） ──────────────────
        BigDecimal discount = BigDecimal.ZERO;
        if (scene == OrderScene.B2C && request.getCouponCode() != null && !request.getCouponCode().isBlank()) {
            discount = new BigDecimal("10.00");
            log.info("B2C coupon applied: couponCode={} discount={}", request.getCouponCode(), discount);
        }
        BigDecimal finalAmount = total.subtract(discount).max(BigDecimal.ZERO);

        Order order = Order.builder()
            .orderNo(orderNoGenerator.next())
            .userId(userId)
            .status(OrderStatus.PENDING)
            .totalAmount(total)
            .discountAmount(discount)
            .finalAmount(finalAmount)
            .paymentMethod(request.getPaymentMethod())
            .shippingName(request.getShippingName())
            .shippingPhone(request.getShippingPhone())
            .shippingAddress(request.getShippingAddress())
            .shippingCity(request.getShippingCity())
            .shippingProvince(request.getShippingProvince())
            .remark(request.getRemark())
            // 场景字段
            .scene(scene)
            .contractNo(request.getContractNo())
            .invoiceRequired(Boolean.TRUE.equals(request.getInvoiceRequired()))
            .invoiceTitle(request.getInvoiceTitle())
            .taxpayerId(request.getTaxpayerId())
            .supplierNo(request.getSupplierNo())
            .couponCode(request.getCouponCode())
            .flashSaleId(request.getFlashSaleId())
            .build();

        List<OrderItem> items = request.getItems().stream()
            .map(i -> OrderItem.builder()
                .order(order)
                .canonicalId(i.getCanonicalId())
                .platform(i.getPlatform())
                .productTitle(i.getProductTitle())
                .unitPrice(i.getUnitPrice())
                .quantity(i.getQuantity())
                .subtotal(i.getUnitPrice().multiply(BigDecimal.valueOf(i.getQuantity())))
                .specs(i.getSpecs())
                .imageUrl(i.getImageUrl())
                .build()
            ).collect(Collectors.toList());

        order.setItems(items);
        Order saved = orderRepository.save(order);

        log.info("Order created: orderNo={} userId={} amount={}", saved.getOrderNo(), userId, total);
        eventPublisher.publishOrderCreated(saved);

        return toDTO(saved);
    }

    // ── 查询 ─────────────────────────────────────────────────────

    @Transactional(readOnly = true)
    public OrderDTO getOrder(Long userId, String orderNo) {
        Order order = orderRepository.findByOrderNo(orderNo)
            .orElseThrow(() -> new IllegalArgumentException("订单不存在: " + orderNo));
        verifyOwnership(userId, order);
        return toDTO(order);
    }

    @Transactional(readOnly = true)
    public PageResult<OrderDTO> listMyOrders(Long userId, OrderStatus status, int page, int size) {
        PageRequest pr = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<Order> pg = (status == null)
            ? orderRepository.findByUserId(userId, pr)
            : orderRepository.findByUserIdAndStatus(userId, status, pr);

        List<OrderDTO> dtos = pg.getContent().stream().map(this::toDTO).collect(Collectors.toList());
        return PageResult.<OrderDTO>builder()
            .content(dtos)
            .totalElements(pg.getTotalElements())
            .totalPages(pg.getTotalPages())
            .page(page)
            .size(size)
            .build();
    }

    // ── 状态变更 ─────────────────────────────────────────────────

    @Transactional
    public OrderDTO payOrder(Long userId, String orderNo) {
        Order order = getAndVerify(userId, orderNo);
        if (order.getStatus() != OrderStatus.PENDING) {
            throw new IllegalStateException("订单状态不可支付: " + order.getStatus());
        }
        order.setStatus(OrderStatus.PAID);
        order.setPaidAt(Instant.now());
        Order saved = orderRepository.save(order);

        log.info("Order paid: orderNo={}", orderNo);
        eventPublisher.publishOrderPaid(saved);
        return toDTO(saved);
    }

    @Transactional
    public OrderDTO cancelOrder(Long userId, String orderNo, String reason) {
        Order order = getAndVerify(userId, orderNo);
        if (order.getStatus() == OrderStatus.SHIPPED || order.getStatus() == OrderStatus.DELIVERED) {
            throw new IllegalStateException("已发货/已完成的订单不能取消");
        }
        if (order.getStatus() == OrderStatus.CANCELLED) {
            throw new IllegalStateException("订单已取消");
        }
        order.setStatus(OrderStatus.CANCELLED);
        order.setCancelledAt(Instant.now());
        order.setCancelReason(reason);
        Order saved = orderRepository.save(order);

        log.info("Order cancelled: orderNo={} reason={}", orderNo, reason);
        eventPublisher.publishOrderCancelled(saved);
        return toDTO(saved);
    }

    /** 仅 ADMIN / 物流系统调用 */
    @Transactional
    public OrderDTO shipOrder(String orderNo) {
        Order order = orderRepository.findByOrderNo(orderNo)
            .orElseThrow(() -> new IllegalArgumentException("订单不存在: " + orderNo));
        if (order.getStatus() != OrderStatus.PAID) {
            throw new IllegalStateException("只有已支付的订单可以发货");
        }
        order.setStatus(OrderStatus.SHIPPED);
        order.setShippedAt(Instant.now());
        return toDTO(orderRepository.save(order));
    }

    @Transactional
    public OrderDTO confirmDelivery(Long userId, String orderNo) {
        Order order = getAndVerify(userId, orderNo);
        if (order.getStatus() != OrderStatus.SHIPPED) {
            throw new IllegalStateException("订单尚未发货");
        }
        order.setStatus(OrderStatus.DELIVERED);
        order.setDeliveredAt(Instant.now());
        Order saved = orderRepository.save(order);

        eventPublisher.publishOrderDelivered(saved);
        return toDTO(saved);
    }

    // ── 内部工具 ─────────────────────────────────────────────────

    private Order getAndVerify(Long userId, String orderNo) {
        Order order = orderRepository.findByOrderNo(orderNo)
            .orElseThrow(() -> new IllegalArgumentException("订单不存在: " + orderNo));
        verifyOwnership(userId, order);
        return order;
    }

    private void verifyOwnership(Long userId, Order order) {
        if (!order.getUserId().equals(userId)) {
            throw new IllegalArgumentException("无权访问该订单");
        }
    }

    private OrderDTO toDTO(Order o) {
        List<OrderItemDTO> itemDTOs = o.getItems().stream()
            .map(i -> OrderItemDTO.builder()
                .id(i.getId())
                .canonicalId(i.getCanonicalId())
                .platform(i.getPlatform())
                .productTitle(i.getProductTitle())
                .unitPrice(i.getUnitPrice())
                .quantity(i.getQuantity())
                .subtotal(i.getSubtotal())
                .specs(i.getSpecs())
                .imageUrl(i.getImageUrl())
                .build())
            .collect(Collectors.toList());

        return OrderDTO.builder()
            .id(o.getId())
            .orderNo(o.getOrderNo())
            .userId(o.getUserId())
            .status(o.getStatus())
            .totalAmount(o.getTotalAmount())
            .discountAmount(o.getDiscountAmount())
            .finalAmount(o.getFinalAmount())
            .paymentMethod(o.getPaymentMethod())
            .shippingName(o.getShippingName())
            .shippingPhone(o.getShippingPhone())
            .shippingAddress(o.getShippingAddress())
            .shippingCity(o.getShippingCity())
            .shippingProvince(o.getShippingProvince())
            .remark(o.getRemark())
            .cancelReason(o.getCancelReason())
            .paidAt(o.getPaidAt())
            .shippedAt(o.getShippedAt())
            .deliveredAt(o.getDeliveredAt())
            .cancelledAt(o.getCancelledAt())
            .createdAt(o.getCreatedAt())
            .items(itemDTOs)
            // 场景字段
            .scene(o.getScene())
            .contractNo(o.getContractNo())
            .invoiceRequired(o.getInvoiceRequired())
            .invoiceTitle(o.getInvoiceTitle())
            .taxpayerId(o.getTaxpayerId())
            .supplierNo(o.getSupplierNo())
            .couponCode(o.getCouponCode())
            .flashSaleId(o.getFlashSaleId())
            .build();
    }
}
