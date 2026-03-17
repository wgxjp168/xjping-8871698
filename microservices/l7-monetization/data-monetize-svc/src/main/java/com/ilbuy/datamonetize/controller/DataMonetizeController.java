package com.ilbuy.datamonetize.controller;

import com.ilbuy.datamonetize.domain.DataProduct;
import com.ilbuy.datamonetize.dto.CreateDataOrderRequest;
import com.ilbuy.datamonetize.dto.DataOrderResponse;
import com.ilbuy.datamonetize.service.DataMonetizeService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1")
@RequiredArgsConstructor
@Slf4j
public class DataMonetizeController {

    private final DataMonetizeService dataMonetizeService;

    @GetMapping("/data-products")
    public ResponseEntity<List<DataProduct>> getAvailableProducts() {
        return ResponseEntity.ok(dataMonetizeService.getAvailableProducts());
    }

    @PostMapping("/data-orders")
    public ResponseEntity<DataOrderResponse> createOrder(@Valid @RequestBody CreateDataOrderRequest req) {
        log.info("[DataMonetizeAPI] Create order: userId={}, productCode={}", req.getUserId(), req.getProductCode());
        return ResponseEntity.ok(dataMonetizeService.createOrder(req));
    }

    @GetMapping("/data-orders/{orderNo}")
    public ResponseEntity<DataOrderResponse> getOrder(@PathVariable String orderNo) {
        return ResponseEntity.ok(dataMonetizeService.getOrder(orderNo));
    }
}
