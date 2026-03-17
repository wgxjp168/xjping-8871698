package com.ilbuy.gateway.service;

import com.alipay.api.AlipayApiException;
import com.alipay.api.AlipayClient;
import com.alipay.api.DefaultAlipayClient;
import com.alipay.api.internal.util.AlipaySignature;
import com.alipay.api.request.AlipayTradeAppPayRequest;
import com.alipay.api.request.AlipayTradePagePayRequest;
import com.alipay.api.request.AlipayTradeRefundRequest;
import com.alipay.api.request.AlipayTradeQueryRequest;
import com.alipay.api.response.AlipayTradeAppPayResponse;
import com.alipay.api.response.AlipayTradePagePayResponse;
import com.alipay.api.response.AlipayTradeRefundResponse;
import com.alipay.api.response.AlipayTradeQueryResponse;
import com.ilbuy.gateway.domain.PaymentOrder;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.util.Map;

/**
 * Alipay integration using the official alipay-sdk-java.
 *
 * Config required:
 *   ilbuy.payment.alipay.app-id
 *   ilbuy.payment.alipay.private-key    (PKCS#8 RSA2 private key, no header/footer, no newlines)
 *   ilbuy.payment.alipay.alipay-public-key  (Alipay platform public key for callback verification)
 *   ilbuy.payment.alipay.notify-url
 *   ilbuy.payment.alipay.return-url     (optional, for PC page-pay redirect)
 */
@Service
@Slf4j
public class AlipayGateway {

    private static final String GATEWAY_URL = "https://openapi.alipay.com/gateway.do";
    private static final String CHARSET     = StandardCharsets.UTF_8.name();
    private static final String FORMAT      = "JSON";
    private static final String SIGN_TYPE   = "RSA2";

    @Value("${ilbuy.payment.alipay.app-id:}")
    private String appId;

    @Value("${ilbuy.payment.alipay.private-key:}")
    private String privateKey;

    @Value("${ilbuy.payment.alipay.alipay-public-key:}")
    private String alipayPublicKey;

    @Value("${ilbuy.payment.alipay.notify-url:http://api.ilbuy.com/api/v1/payments/alipay/notify}")
    private String notifyUrl;

    @Value("${ilbuy.payment.alipay.return-url:}")
    private String returnUrl;

    private AlipayClient alipayClient;

    @PostConstruct
    public void init() {
        if (appId.isBlank() || privateKey.isBlank() || alipayPublicKey.isBlank()) {
            log.warn("[Alipay] SDK config incomplete — running in stub mode");
            return;
        }
        alipayClient = new DefaultAlipayClient(GATEWAY_URL, appId, privateKey,
            FORMAT, CHARSET, alipayPublicKey, SIGN_TYPE);
        log.info("[Alipay] SDK initialised, appId={}", appId);
    }

    private boolean isSdkReady() {
        return alipayClient != null;
    }

    /**
     * Create PC web payment (alipay.trade.page.pay).
     * Returns a signed HTML form; submit it to redirect user to Alipay.
     */
    public Map<String, Object> createPageOrder(PaymentOrder order) {
        if (!isSdkReady()) return stubOrder(order, "PAGE");

        AlipayTradePagePayRequest req = new AlipayTradePagePayRequest();
        req.setNotifyUrl(notifyUrl);
        if (!returnUrl.isBlank()) req.setReturnUrl(returnUrl);
        req.setBizContent(String.format(
            "{\"out_trade_no\":\"%s\",\"total_amount\":\"%s\",\"subject\":\"%s\",\"product_code\":\"FAST_INSTANT_TRADE_PAY\"}",
            order.getBizOrderNo(), order.getAmount().toPlainString(), order.getSubject()));
        try {
            AlipayTradePagePayResponse resp = alipayClient.pageExecute(req);
            return Map.of(
                "trade_type", "PAGE",
                "out_trade_no", order.getBizOrderNo(),
                "payment_form", resp.getBody()   // signed POST form HTML
            );
        } catch (AlipayApiException e) {
            throw new RuntimeException("[Alipay] createPageOrder failed: " + e.getErrMsg(), e);
        }
    }

    /**
     * Create App payment string (alipay.trade.app.pay).
     * Returns the signed orderString for the iOS/Android Alipay SDK.
     */
    public Map<String, Object> createAppOrder(PaymentOrder order) {
        if (!isSdkReady()) return stubOrder(order, "APP");

        AlipayTradeAppPayRequest req = new AlipayTradeAppPayRequest();
        req.setNotifyUrl(notifyUrl);
        req.setBizContent(String.format(
            "{\"out_trade_no\":\"%s\",\"total_amount\":\"%s\",\"subject\":\"%s\",\"product_code\":\"QUICK_MSECURITY_PAY\"}",
            order.getBizOrderNo(), order.getAmount().toPlainString(), order.getSubject()));
        try {
            AlipayTradeAppPayResponse resp = alipayClient.sdkExecute(req);
            return Map.of(
                "trade_type", "APP",
                "out_trade_no", order.getBizOrderNo(),
                "order_string", resp.getBody()  // signed string for mobile SDK
            );
        } catch (AlipayApiException e) {
            throw new RuntimeException("[Alipay] createAppOrder failed: " + e.getErrMsg(), e);
        }
    }

    /**
     * Unified entry — uses Page pay by default (suitable for web/H5).
     */
    public Map<String, Object> createOrder(PaymentOrder order, String buyerLogonId) {
        return createPageOrder(order);
    }

    /**
     * Apply refund (alipay.trade.refund).
     * @return Alipay trade_no on success
     */
    public String refund(String tradeNo, String refundNo, BigDecimal refundAmount) {
        log.info("[Alipay] Refund: tradeNo={}, refundNo={}, amount={}", tradeNo, refundNo, refundAmount);
        if (!isSdkReady()) return "ALI_REFUND_STUB_" + refundNo;

        AlipayTradeRefundRequest req = new AlipayTradeRefundRequest();
        req.setBizContent(String.format(
            "{\"trade_no\":\"%s\",\"refund_amount\":\"%s\",\"out_request_no\":\"%s\"}",
            tradeNo, refundAmount.toPlainString(), refundNo));
        try {
            AlipayTradeRefundResponse resp = alipayClient.execute(req);
            if (resp.isSuccess()) {
                log.info("[Alipay] Refund success: tradeNo={}", resp.getTradeNo());
                return resp.getTradeNo();
            }
            throw new RuntimeException("[Alipay] Refund failed: " + resp.getSubMsg());
        } catch (AlipayApiException e) {
            throw new RuntimeException("[Alipay] refund API error: " + e.getErrMsg(), e);
        }
    }

    /**
     * Query trade status (alipay.trade.query).
     * Returns "TRADE_SUCCESS", "TRADE_CLOSED", "WAIT_BUYER_PAY", etc.
     */
    public String queryTradeStatus(String outTradeNo) {
        if (!isSdkReady()) return "UNKNOWN";

        AlipayTradeQueryRequest req = new AlipayTradeQueryRequest();
        req.setBizContent(String.format("{\"out_trade_no\":\"%s\"}", outTradeNo));
        try {
            AlipayTradeQueryResponse resp = alipayClient.execute(req);
            return resp.isSuccess() ? resp.getTradeStatus() : "UNKNOWN";
        } catch (AlipayApiException e) {
            log.error("[Alipay] queryTradeStatus error: {}", e.getMessage());
            return "UNKNOWN";
        }
    }

    /**
     * Verify Alipay async notification signature using RSA2.
     * Must be called before processing any notify callback.
     */
    public boolean verifySignature(Map<String, String> params) {
        if (!isSdkReady()) {
            log.warn("[Alipay] SDK not ready — skipping signature verification (STUB mode)");
            return false;
        }
        try {
            return AlipaySignature.rsaCheckV1(params, alipayPublicKey, CHARSET, SIGN_TYPE);
        } catch (AlipayApiException e) {
            log.error("[Alipay] Signature verification error: {}", e.getMessage());
            return false;
        }
    }

    private Map<String, Object> stubOrder(PaymentOrder order, String tradeType) {
        log.warn("[Alipay] STUB mode — returning mock order for {}", order.getBizOrderNo());
        return Map.of(
            "stub",        true,
            "trade_type",  tradeType,
            "out_trade_no", order.getBizOrderNo(),
            "payment_form", "<!-- Alipay STUB -->"
        );
    }
}
