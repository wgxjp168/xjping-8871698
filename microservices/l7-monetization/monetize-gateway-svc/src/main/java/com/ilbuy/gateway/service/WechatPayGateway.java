package com.ilbuy.gateway.service;

import com.wechat.pay.java.core.RSAAutoCertificateConfig;
import com.wechat.pay.java.core.notification.NotificationConfig;
import com.wechat.pay.java.core.notification.NotificationParser;
import com.wechat.pay.java.core.notification.RequestParam;
import com.wechat.pay.java.service.payments.jsapi.JsapiServiceExtension;
import com.wechat.pay.java.service.payments.jsapi.model.Amount;
import com.wechat.pay.java.service.payments.jsapi.model.Payer;
import com.wechat.pay.java.service.payments.jsapi.model.PrepayRequest;
import com.wechat.pay.java.service.payments.jsapi.model.PrepayWithRequestPaymentResponse;
import com.wechat.pay.java.service.payments.nativepay.NativePayService;
import com.wechat.pay.java.service.payments.nativepay.model.PrepayResponse;
import com.wechat.pay.java.service.payments.model.Transaction;
import com.wechat.pay.java.service.refund.RefundService;
import com.wechat.pay.java.service.refund.model.AmountReq;
import com.wechat.pay.java.service.refund.model.CreateRequest;
import com.wechat.pay.java.service.refund.model.Refund;
import com.ilbuy.gateway.domain.PaymentOrder;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import java.math.BigDecimal;
import java.util.Map;

/**
 * WeChat Pay V3 gateway using the official wechatpay-java SDK.
 * Handles JSAPI (mini-program/H5), Native (QR), refunds, and callback decryption.
 *
 * Config required:
 *   ilbuy.payment.wechat.mch-id
 *   ilbuy.payment.wechat.private-key-path   (PKCS#8 PEM, e.g. /run/secrets/wxpay_private_key.pem)
 *   ilbuy.payment.wechat.merchant-serial-number
 *   ilbuy.payment.wechat.api-v3-key         (32-byte API v3 key for AES-GCM callback decryption)
 *   ilbuy.payment.wechat.app-id
 */
@Service
@Slf4j
public class WechatPayGateway {

    @Value("${ilbuy.payment.wechat.app-id:}")
    private String appId;

    @Value("${ilbuy.payment.wechat.mch-id:}")
    private String mchId;

    @Value("${ilbuy.payment.wechat.private-key-path:}")
    private String privateKeyPath;

    @Value("${ilbuy.payment.wechat.merchant-serial-number:}")
    private String merchantSerialNumber;

    @Value("${ilbuy.payment.wechat.api-v3-key:}")
    private String apiV3Key;

    @Value("${ilbuy.payment.wechat.notify-url:http://api.ilbuy.com/api/v1/payments/wechat/notify}")
    private String notifyUrl;

    private RSAAutoCertificateConfig config;
    private JsapiServiceExtension jsapiService;
    private NativePayService nativePayService;
    private RefundService refundService;
    private NotificationParser notificationParser;

    @PostConstruct
    public void init() {
        if (mchId.isBlank() || merchantSerialNumber.isBlank() || apiV3Key.isBlank()) {
            log.warn("[WechatPay] SDK config incomplete — running in stub mode (no credentials configured)");
            return;
        }
        try {
            config = new RSAAutoCertificateConfig.Builder()
                .merchantId(mchId)
                .privateKeyFromPath(privateKeyPath)
                .merchantSerialNumber(merchantSerialNumber)
                .apiV3Key(apiV3Key)
                .build();
            jsapiService  = new JsapiServiceExtension.Builder().config(config).build();
            nativePayService = new NativePayService.Builder().config(config).build();
            refundService = new RefundService.Builder().config(config).build();
            notificationParser = new NotificationParser((NotificationConfig) config);
            log.info("[WechatPay] V3 SDK initialised, mchId={}", mchId);
        } catch (Exception e) {
            log.error("[WechatPay] SDK init failed: {}", e.getMessage(), e);
        }
    }

    private boolean isSdkReady() {
        return config != null && jsapiService != null;
    }

    /**
     * JSAPI prepay (mini-program / WeChat H5).
     * Returns signed params for wx.requestPayment().
     */
    public Map<String, Object> jsapiPrepay(PaymentOrder order, String openId) {
        if (!isSdkReady()) return stubPrepay(order, "JSAPI");

        PrepayRequest req = new PrepayRequest();
        req.setAppid(appId);
        req.setMchid(mchId);
        req.setDescription(order.getSubject());
        req.setOutTradeNo(order.getBizOrderNo());
        req.setNotifyUrl(notifyUrl);
        Amount amount = new Amount();
        amount.setTotal(toFen(order.getAmount()));
        amount.setCurrency("CNY");
        req.setAmount(amount);
        Payer payer = new Payer();
        payer.setOpenid(openId);
        req.setPayer(payer);

        PrepayWithRequestPaymentResponse resp = jsapiService.prepayWithRequestPayment(req);
        return Map.of(
            "appId",     resp.getAppId(),
            "timeStamp", resp.getTimeStamp(),
            "nonceStr",  resp.getNonceStr(),
            "package",   resp.getPackageVal(),
            "signType",  resp.getSignType(),
            "paySign",   resp.getPaySign()
        );
    }

    /**
     * Native pay (QR code). Returns code_url.
     */
    public Map<String, Object> nativePrepay(PaymentOrder order) {
        if (!isSdkReady()) return stubPrepay(order, "NATIVE");

        com.wechat.pay.java.service.payments.nativepay.model.PrepayRequest req =
            new com.wechat.pay.java.service.payments.nativepay.model.PrepayRequest();
        req.setAppid(appId);
        req.setMchid(mchId);
        req.setDescription(order.getSubject());
        req.setOutTradeNo(order.getBizOrderNo());
        req.setNotifyUrl(notifyUrl);
        com.wechat.pay.java.service.payments.nativepay.model.Amount nativeAmount =
            new com.wechat.pay.java.service.payments.nativepay.model.Amount();
        nativeAmount.setTotal(toFen(order.getAmount()));
        req.setAmount(nativeAmount);

        PrepayResponse resp = nativePayService.prepay(req);
        return Map.of("code_url", resp.getCodeUrl(), "trade_type", "NATIVE");
    }

    /**
     * Unified entry: JSAPI when openId present, otherwise Native QR.
     */
    public Map<String, Object> unifiedOrder(PaymentOrder order, String openId) {
        if (openId != null && !openId.isBlank()) {
            return jsapiPrepay(order, openId);
        }
        return nativePrepay(order);
    }

    /**
     * Apply refund via WeChat Pay V3 refund API.
     * @return WeChat refund ID
     */
    public String refund(String transactionId, String refundNo, BigDecimal refundAmount, BigDecimal totalAmount) {
        log.info("[WechatPay] Refund: transactionId={}, refundNo={}, amount={}", transactionId, refundNo, refundAmount);
        if (!isSdkReady()) return "WX_REFUND_STUB_" + refundNo;

        CreateRequest req = new CreateRequest();
        req.setTransactionId(transactionId);
        req.setOutRefundNo(refundNo);
        AmountReq amtReq = new AmountReq();
        amtReq.setRefund(toFen(refundAmount));
        amtReq.setTotal(toFen(totalAmount));
        amtReq.setCurrency("CNY");
        req.setAmount(amtReq);

        Refund resp = refundService.create(req);
        log.info("[WechatPay] Refund submitted: wechatRefundId={}", resp.getRefundId());
        return resp.getRefundId();
    }

    /**
     * Parse and cryptographically verify a V3 payment callback notification.
     *
     * The SDK checks the RSA signature carried in HTTP headers (Wechatpay-Timestamp,
     * Wechatpay-Nonce, Wechatpay-Signature, Wechatpay-Serial) and decrypts the
     * AES-256-GCM ciphertext in the resource field using the API v3 key.
     *
     * @return Parsed Transaction, or null when signature/decryption fails
     */
    public Transaction parseNotification(String timestamp, String nonce, String signature,
                                          String serialNumber, String body) {
        if (!isSdkReady()) {
            log.warn("[WechatPay] SDK not initialised — cannot verify V3 notification");
            return null;
        }
        try {
            RequestParam requestParam = new RequestParam.Builder()
                .serialNumber(serialNumber)
                .nonce(nonce)
                .signature(signature)
                .timestamp(timestamp)
                .body(body)
                .build();
            return notificationParser.parse(requestParam, Transaction.class);
        } catch (Exception e) {
            log.error("[WechatPay] Notification parse/verify failed: {}", e.getMessage());
            return null;
        }
    }

    /** @deprecated V3 no longer uses the old XML params map. Use parseNotification(). */
    public boolean verifySignature(Map<String, String> params) {
        return false;
    }

    private int toFen(BigDecimal yuan) {
        return yuan.multiply(BigDecimal.valueOf(100)).intValue();
    }

    private Map<String, Object> stubPrepay(PaymentOrder order, String tradeType) {
        log.warn("[WechatPay] STUB mode — returning mock prepay for order {}", order.getBizOrderNo());
        return Map.of(
            "stub",        true,
            "trade_type",  tradeType,
            "out_trade_no", order.getBizOrderNo(),
            "prepay_id",   "wx_stub_" + System.currentTimeMillis()
        );
    }
}
