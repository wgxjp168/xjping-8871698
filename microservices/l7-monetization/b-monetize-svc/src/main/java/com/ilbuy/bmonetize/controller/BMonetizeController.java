package com.ilbuy.bmonetize.controller;

import com.ilbuy.bmonetize.dto.*;
import com.ilbuy.bmonetize.service.BMonetizeService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/internal/v1/b-orders")
@RequiredArgsConstructor
@Slf4j
public class BMonetizeController {

    private final BMonetizeService bMonetizeService;

    @PostMapping
    public ResponseEntity<BOrderResponse> createOrder(@Valid @RequestBody CreateBOrderRequest req) {
        log.info("[BMonetizeAPI] Create order: corpId={}, type={}", req.getCorpId(), req.getProductType());
        return ResponseEntity.ok(bMonetizeService.createOrder(req));
    }

    @GetMapping("/{orderNo}")
    public ResponseEntity<BOrderResponse> getOrder(@PathVariable String orderNo) {
        return ResponseEntity.ok(bMonetizeService.getOrder(orderNo));
    }
}
