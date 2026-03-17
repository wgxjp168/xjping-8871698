package com.ilbuy.gateway.controller;

import com.ilbuy.gateway.dto.*;
import com.ilbuy.gateway.service.PaymentGatewayService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/payments")
@RequiredArgsConstructor
@Slf4j
public class PaymentController {

    private final PaymentGatewayService paymentGatewayService;

    @PostMapping
    public ResponseEntity<PaymentResponse> createPayment(@Valid @RequestBody CreatePaymentRequest request) {
        log.info("[PaymentAPI] Create payment for bizOrderNo={}", request.getBizOrderNo());
        return ResponseEntity.ok(paymentGatewayService.createPayment(request));
    }

    @GetMapping("/{paymentNo}")
    public ResponseEntity<PaymentResponse> queryPayment(@PathVariable String paymentNo) {
        return ResponseEntity.ok(paymentGatewayService.queryPayment(paymentNo));
    }

    @PostMapping("/{paymentNo}/refund")
    public ResponseEntity<RefundResponse> refund(
            @PathVariable String paymentNo,
            @Valid @RequestBody RefundRequest request) {
        request.setPaymentNo(paymentNo);
        return ResponseEntity.ok(paymentGatewayService.applyRefund(request));
    }
}
