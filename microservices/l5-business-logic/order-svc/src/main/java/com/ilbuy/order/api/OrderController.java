package com.ilbuy.order.api;

import com.ilbuy.order.model.dto.*;
import com.ilbuy.order.model.enums.OrderStatus;
import com.ilbuy.order.service.OrderService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/orders")
@RequiredArgsConstructor
public class OrderController {

    private final OrderService orderService;

    /** 创建订单 */
    @PostMapping
    public ResponseEntity<OrderDTO> create(
        @AuthenticationPrincipal Long userId,
        @Valid @RequestBody CreateOrderRequest request
    ) {
        return ResponseEntity.ok(orderService.createOrder(userId, request));
    }

    /** 获取单个订单详情 */
    @GetMapping("/{orderNo}")
    public ResponseEntity<OrderDTO> getOrder(
        @AuthenticationPrincipal Long userId,
        @PathVariable String orderNo
    ) {
        return ResponseEntity.ok(orderService.getOrder(userId, orderNo));
    }

    /** 分页查询我的订单 */
    @GetMapping
    public ResponseEntity<PageResult<OrderDTO>> listMyOrders(
        @AuthenticationPrincipal Long userId,
        @RequestParam(required = false) OrderStatus status,
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "10") int size
    ) {
        return ResponseEntity.ok(orderService.listMyOrders(userId, status, page, size));
    }

    /** 支付订单（模拟，实际应对接支付网关回调） */
    @PostMapping("/{orderNo}/pay")
    public ResponseEntity<OrderDTO> pay(
        @AuthenticationPrincipal Long userId,
        @PathVariable String orderNo
    ) {
        return ResponseEntity.ok(orderService.payOrder(userId, orderNo));
    }

    /** 取消订单 */
    @PostMapping("/{orderNo}/cancel")
    public ResponseEntity<OrderDTO> cancel(
        @AuthenticationPrincipal Long userId,
        @PathVariable String orderNo,
        @RequestParam(defaultValue = "用户主动取消") String reason
    ) {
        return ResponseEntity.ok(orderService.cancelOrder(userId, orderNo, reason));
    }

    /** 确认收货 */
    @PostMapping("/{orderNo}/confirm-delivery")
    public ResponseEntity<OrderDTO> confirmDelivery(
        @AuthenticationPrincipal Long userId,
        @PathVariable String orderNo
    ) {
        return ResponseEntity.ok(orderService.confirmDelivery(userId, orderNo));
    }

    /** 内部接口：发货（仅 ADMIN） */
    @PostMapping("/internal/{orderNo}/ship")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<OrderDTO> ship(@PathVariable String orderNo) {
        return ResponseEntity.ok(orderService.shipOrder(orderNo));
    }
}
