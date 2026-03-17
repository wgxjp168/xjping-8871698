package com.ilbuy.cmonetize.controller;

import com.ilbuy.cmonetize.dto.*;
import com.ilbuy.cmonetize.service.CMonetizeService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/internal/v1/c-orders")
@RequiredArgsConstructor
@Slf4j
public class CMonetizeController {

    private final CMonetizeService cMonetizeService;

    @PostMapping
    public ResponseEntity<OrderResponse> createOrder(@Valid @RequestBody CreateOrderRequest req) {
        log.info("[CMonetizeAPI] Create order: userId={}, type={}", req.getUserId(), req.getProductType());
        return ResponseEntity.ok(cMonetizeService.createOrder(req));
    }

    @GetMapping("/{orderNo}")
    public ResponseEntity<OrderResponse> getOrder(@PathVariable String orderNo) {
        return ResponseEntity.ok(cMonetizeService.getOrder(orderNo));
    }

    @GetMapping("/user/{userId}")
    public ResponseEntity<List<OrderResponse>> getUserOrders(@PathVariable Long userId) {
        return ResponseEntity.ok(cMonetizeService.getUserOrders(userId));
    }
}
