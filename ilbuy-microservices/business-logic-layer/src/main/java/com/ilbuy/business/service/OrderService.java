package com.ilbuy.business.service;

import com.ilbuy.business.exception.ResourceNotFoundException;
import com.ilbuy.business.model.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;

@Service
public class OrderService {

    private static final Logger log = LoggerFactory.getLogger(OrderService.class);
    private final Map<String, Order> orders = new ConcurrentHashMap<>();
    private final AtomicInteger orderSeq = new AtomicInteger(1000);
    private final ProductService productService;

    public OrderService(ProductService productService) {
        this.productService = productService;
    }

    public Order createOrder(String userId, List<OrderItem> items, String shippingAddress, String paymentMethod) {
        String orderId = "ORD" + orderSeq.incrementAndGet();
        Order order = new Order(orderId, userId);
        order.setShippingAddress(shippingAddress);
        order.setPaymentMethod(paymentMethod);

        for (OrderItem item : items) {
            Product product = productService.findById(item.getProductId());
            productService.deductStock(product.getId(), item.getQuantity());
            item.setProductName(product.getName());
            item.setPrice(product.getPrice());
            order.addItem(item);
        }

        orders.put(orderId, order);
        log.info("创建订单: orderId={}, userId={}, total={}", orderId, userId, order.getTotalAmount());
        return order;
    }

    public List<Order> findByUserId(String userId) {
        return orders.values().stream()
                .filter(o -> o.getUserId().equals(userId))
                .collect(Collectors.toList());
    }

    public Order findById(String orderId) {
        Order order = orders.get(orderId);
        if (order == null) throw new ResourceNotFoundException("订单不存在: " + orderId);
        return order;
    }

    public List<Order> findAll() {
        return new ArrayList<>(orders.values());
    }

    public Order updateStatus(String orderId, String newStatus) {
        Order order = findById(orderId);
        String oldStatus = order.getStatus();
        order.setStatus(newStatus);
        log.info("订单状态变更: orderId={}, {} -> {}", orderId, oldStatus, newStatus);
        return order;
    }

    public Order cancelOrder(String orderId) {
        Order order = findById(orderId);
        if (!"PENDING".equals(order.getStatus()) && !"PAID".equals(order.getStatus())) {
            throw new IllegalStateException("订单状态 %s 不允许取消".formatted(order.getStatus()));
        }
        order.setStatus("CANCELLED");
        log.info("取消订单: orderId={}", orderId);
        return order;
    }
}
