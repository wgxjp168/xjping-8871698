package com.ilbuy.business.controller;

import com.ilbuy.business.model.Order;
import com.ilbuy.business.model.OrderItem;
import com.ilbuy.business.service.OrderService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/orders")
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @GetMapping
    public ResponseEntity<List<Order>> listOrders(
            @RequestParam(required = false) String userId) {
        if (userId != null) return ResponseEntity.ok(orderService.findByUserId(userId));
        return ResponseEntity.ok(orderService.findAll());
    }

    @GetMapping("/{orderId}")
    public ResponseEntity<Order> getOrder(@PathVariable String orderId) {
        return ResponseEntity.ok(orderService.findById(orderId));
    }

    @PostMapping
    public ResponseEntity<Order> createOrder(@RequestBody Map<String, Object> payload) {
        String userId = (String) payload.get("userId");
        String shippingAddress = (String) payload.get("shippingAddress");
        String paymentMethod = (String) payload.getOrDefault("paymentMethod", "ONLINE");

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> rawItems = (List<Map<String, Object>>) payload.get("items");

        List<OrderItem> items = rawItems.stream().map(m -> new OrderItem(
                (String) m.get("productId"),
                null,
                0,
                ((Number) m.get("quantity")).intValue()
        )).toList();

        Order order = orderService.createOrder(userId, items, shippingAddress, paymentMethod);
        return ResponseEntity.status(HttpStatus.CREATED).body(order);
    }

    @PutMapping("/{orderId}/status")
    public ResponseEntity<Order> updateStatus(
            @PathVariable String orderId,
            @RequestBody Map<String, String> body) {
        return ResponseEntity.ok(orderService.updateStatus(orderId, body.get("status")));
    }

    @PostMapping("/{orderId}/cancel")
    public ResponseEntity<Order> cancelOrder(@PathVariable String orderId) {
        return ResponseEntity.ok(orderService.cancelOrder(orderId));
    }
}
