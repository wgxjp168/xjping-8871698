package com.ilbuy.gateway.service;

import com.ilbuy.gateway.dto.*;
import com.ilbuy.gateway.domain.PaymentOrder;
import java.util.Map;

public interface PaymentGatewayService {
    PaymentResponse createPayment(CreatePaymentRequest request);
    PaymentResponse queryPayment(String paymentNo);
    RefundResponse applyRefund(RefundRequest request);
    /** Process payment callback from channel, returns "SUCCESS" or "FAIL" */
    String handleCallback(String channel, Map<String, String> params, String rawBody);
}
