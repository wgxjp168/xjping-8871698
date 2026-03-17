package com.ilbuy.gateway.service;

import com.ilbuy.gateway.domain.PaymentOrder;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import java.math.BigDecimal;
import java.util.*;

/**
 * WeChat Pay V3 Native/JSAPI integration.
 * Production: replace stub methods with WeChatPay Java SDK or direct V3 REST calls.
 */
@Service
@Slf4j
public class WechatPayGateway {

    @Value("${ilbuy.payment.wechat.app-id:}")
    private String appId;

    @Value("${ilbuy.payment.wechat.mch-id:}")
    private String mchId;

    @Value("${ilbuy.payment.wechat.api-key:}")
    private String apiKey;

    @Value("${ilbuy.payment.wechat.notify-url:}")
    private String notifyUrl;

    private final RestTemplate restTemplate = new RestTemplate();

    /**
     * Create WeChat Pay unified order. Returns prepay params for JSAPI or code_url for Native.
     */
    public Map<String, Object> unifiedOrder(PaymentOrder order, String openId) {
        log.info("[WechatPay] Creating order: paymentNo={}, amount={}", order.getPaymentNo(), order.getAmount());
        // TODO: Replace with actual WeChat Pay V3 API call
        // POST https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi
        Map<String, Object> params = new LinkedHashMap<>();
        params.put("appid", appId);
        params.put("mchid", mchId);
        params.put("description", order.getSubject());
        params.put("out_trade_no", order.getBizOrderNo());
        params.put("notify_url", notifyUrl);
        params.put("amount", Map.of("total", order.getAmount().multiply(BigDecimal.valueOf(100)).intValue(), "currency", "CNY"));
        if (openId != null) params.put("payer", Map.of("openid", openId));

        // Return simulated prepay_id for integration environments
        return Map.of(
            "prepay_id", "wx" + System.currentTimeMillis(),
            "timeStamp", String.valueOf(System.currentTimeMillis() / 1000),
            "nonceStr", UUID.randomUUID().toString().replace("-", ""),
            "package", "prepay_id=wx" + System.currentTimeMillis(),
            "signType", "RSA"
        );
    }

    public String refund(String transactionId, String refundNo, BigDecimal refundAmount, BigDecimal totalAmount) {
        log.info("[WechatPay] Refund: transactionId={}, refundNo={}, amount={}", transactionId, refundNo, refundAmount);
        // POST https://api.mch.weixin.qq.com/v3/refund/domestic/refunds
        return "WX_REFUND_" + refundNo;
    }

    public boolean verifySignature(Map<String, String> params) {
        // TODO: Implement WeChat Pay V3 signature verification using API v3 key
        log.debug("[WechatPay] Verifying signature for params: {}", params.keySet());
        return true; // Replace with actual RSA signature verification
    }
}
