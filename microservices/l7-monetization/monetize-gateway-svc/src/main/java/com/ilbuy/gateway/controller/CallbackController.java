package com.ilbuy.gateway.controller;

import com.ilbuy.gateway.service.PaymentGatewayService;
import com.ilbuy.gateway.service.WechatPayGateway;
import com.wechat.pay.java.service.payments.model.Transaction;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Payment channel callback endpoints.
 * These URLs are whitelisted (no JWT required) in SecurityConfig.
 *
 * WeChat Pay V3: JSON body + RSA signature in HTTP headers.
 * Alipay:        form-encoded parameters + RSA2 signature in sign field.
 */
@RestController
@RequestMapping("/api/v1/payments")
@RequiredArgsConstructor
@Slf4j
public class CallbackController {

    private final PaymentGatewayService paymentGatewayService;
    private final WechatPayGateway wechatPayGateway;

    /**
     * WeChat Pay V3 payment result notification.
     * WeChat sends JSON with AES-256-GCM encrypted resource; the SDK decrypts it.
     * Response must be HTTP 200 with JSON {"code":"SUCCESS"} on success.
     */
    @PostMapping(value = "/wechat/notify", consumes = MediaType.APPLICATION_JSON_VALUE,
                 produces = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<Map<String, String>> wechatNotify(
            HttpServletRequest request,
            @RequestHeader(value = "Wechatpay-Timestamp", required = false)  String timestamp,
            @RequestHeader(value = "Wechatpay-Nonce",     required = false)  String nonce,
            @RequestHeader(value = "Wechatpay-Signature", required = false)  String signature,
            @RequestHeader(value = "Wechatpay-Serial",    required = false)  String serial) {

        log.info("[Callback] WeChat Pay V3 callback received");
        try {
            String body = new BufferedReader(
                new InputStreamReader(request.getInputStream(), StandardCharsets.UTF_8))
                .lines().collect(Collectors.joining());

            // Use SDK to verify RSA signature and decrypt AES-256-GCM payload
            Transaction tx = wechatPayGateway.parseNotification(timestamp, nonce, signature, serial, body);
            if (tx == null) {
                log.warn("[Callback] WeChat signature verification failed");
                return ResponseEntity.ok(Map.of("code", "FAIL", "message", "Signature verification failed"));
            }

            // Build params map from decrypted transaction
            Map<String, String> params = new HashMap<>();
            params.put("transaction_id", tx.getTransactionId());
            params.put("out_trade_no",   tx.getOutTradeNo());
            params.put("result_code",    tx.getTradeState() != null ? tx.getTradeState().name() : "");
            params.put("trade_state",    tx.getTradeState() != null ? tx.getTradeState().name() : "");

            paymentGatewayService.handleCallback("WECHAT", params, body);
            return ResponseEntity.ok(Map.of("code", "SUCCESS"));
        } catch (Exception e) {
            log.error("[Callback] WeChat notify error: {}", e.getMessage(), e);
            return ResponseEntity.ok(Map.of("code", "FAIL", "message", e.getMessage()));
        }
    }

    /**
     * Alipay async notification.
     * Alipay sends form-encoded POST; must return "success" plain text on success.
     */
    @PostMapping(value = "/alipay/notify", consumes = MediaType.APPLICATION_FORM_URLENCODED_VALUE)
    public String alipayNotify(HttpServletRequest request) {
        log.info("[Callback] Alipay callback received");
        Map<String, String> params = new HashMap<>();
        request.getParameterMap().forEach((k, v) -> params.put(k, v[0]));

        // PaymentGatewayServiceImpl.handleCallback("ALIPAY", ...) calls AlipayGateway.verifySignature()
        String result = paymentGatewayService.handleCallback("ALIPAY", params, params.toString());
        return "SUCCESS".equalsIgnoreCase(result) ? "success" : "failure";
    }
}
