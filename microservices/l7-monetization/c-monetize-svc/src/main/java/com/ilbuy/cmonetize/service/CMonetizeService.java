package com.ilbuy.cmonetize.service;

import com.ilbuy.cmonetize.domain.CMonetizeOrder;
import com.ilbuy.cmonetize.domain.CMonetizeOrder.*;
import com.ilbuy.cmonetize.domain.MembershipPlan;
import com.ilbuy.cmonetize.dto.*;
import com.ilbuy.cmonetize.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;

@Service
@RequiredArgsConstructor
@Slf4j
public class CMonetizeService {

    private final CMonetizeOrderRepository orderRepository;
    private final MembershipPlanRepository planRepository;
    private final RestTemplate restTemplate;

    @Value("${ilbuy.gateway.url:http://monetize-gateway-svc:8071}")
    private String gatewayUrl;

    /** Single-report price in CNY */
    private static final BigDecimal SINGLE_REPORT_PRICE = new BigDecimal("99.00");

    @Transactional
    public OrderResponse createOrder(CreateOrderRequest req) {
        BigDecimal amount = resolveAmount(req);
        String orderNo = "CO-" + UUID.randomUUID().toString().replace("-", "").toUpperCase().substring(0, 16);

        CMonetizeOrder order = CMonetizeOrder.builder()
            .orderNo(orderNo)
            .userId(req.getUserId())
            .productType(req.getProductType())
            .productId(req.getProductId())
            .amount(amount)
            .status(OrderStatus.PENDING_PAYMENT)
            .l5OrderNo(req.getL5OrderNo())
            .l6ReportNo(req.getProductType() == ProductType.SINGLE_REPORT ? req.getProductId() : null)
            .expiredAt(LocalDateTime.now().plusMinutes(30))
            .build();
        orderRepository.save(order);

        // Auto-renewal orders are fulfilled by the scheduled job; no gateway payment needed here.
        // The subscription will be extended when a real payment confirmation arrives.
        if ("AUTO_RENEWAL".equalsIgnoreCase(req.getPaymentChannel())) {
            log.info("[CMonetize] Auto-renewal order created (gateway call skipped): orderNo={}", orderNo);
            return buildResponse(order, null);
        }

        // Call payment gateway to create payment
        Map<String, Object> gatewayReq = new HashMap<>();
        gatewayReq.put("bizOrderNo", orderNo);
        gatewayReq.put("userId", req.getUserId());
        gatewayReq.put("amount", amount);
        gatewayReq.put("channel", req.getPaymentChannel());
        gatewayReq.put("bizType", req.getProductType() == ProductType.SINGLE_REPORT ? "C_SINGLE" : "C_MEMBER");
        gatewayReq.put("subject", resolveSubject(req));
        if (req.getChannelUserId() != null) gatewayReq.put("channelUserId", req.getChannelUserId());

        Object channelParams = null;
        try {
            ResponseEntity<Map> resp = restTemplate.postForEntity(gatewayUrl + "/api/v1/payments", gatewayReq, Map.class);
            if (resp.getStatusCode() == HttpStatus.OK && resp.getBody() != null) {
                order.setPaymentNo((String) resp.getBody().get("paymentNo"));
                orderRepository.save(order);
                channelParams = resp.getBody().get("channelPayParams");
            }
        } catch (Exception e) {
            log.error("[CMonetize] Gateway call failed for order {}: {}", orderNo, e.getMessage());
        }

        log.info("[CMonetize] Order created: orderNo={}, userId={}, amount={}", orderNo, req.getUserId(), amount);
        return buildResponse(order, channelParams);
    }

    @Transactional
    public void confirmPayment(String paymentNo, String bizOrderNo) {
        CMonetizeOrder order = orderRepository.findByOrderNo(bizOrderNo)
            .orElseGet(() -> orderRepository.findByPaymentNo(paymentNo).orElse(null));
        if (order == null) { log.warn("[CMonetize] Order not found for confirm: {}", bizOrderNo); return; }
        if (order.getStatus() == OrderStatus.PAID) return; // idempotent

        order.setStatus(OrderStatus.PAID);
        order.setPaymentNo(paymentNo);
        order.setPaidAt(LocalDateTime.now());
        orderRepository.save(order);
        log.info("[CMonetize] Order confirmed: orderNo={}", order.getOrderNo());
    }

    @Transactional(readOnly = true)
    public OrderResponse getOrder(String orderNo) {
        CMonetizeOrder order = orderRepository.findByOrderNo(orderNo)
            .orElseThrow(() -> new IllegalArgumentException("Order not found: " + orderNo));
        return buildResponse(order, null);
    }

    @Transactional(readOnly = true)
    public List<OrderResponse> getUserOrders(Long userId) {
        return orderRepository.findByUserIdOrderByCreatedAtDesc(userId)
            .stream().map(o -> buildResponse(o, null)).toList();
    }

    private BigDecimal resolveAmount(CreateOrderRequest req) {
        if (req.getProductType() == ProductType.SINGLE_REPORT) return SINGLE_REPORT_PRICE;
        MembershipPlan plan = planRepository.findByPlanCode(req.getProductId())
            .orElseThrow(() -> new IllegalArgumentException("Plan not found: " + req.getProductId()));
        return plan.getPrice();
    }

    private String resolveSubject(CreateOrderRequest req) {
        return req.getProductType() == ProductType.SINGLE_REPORT
            ? "ILbuy单次报告付费"
            : "ILbuy会员订阅 - " + req.getProductId();
    }

    private OrderResponse buildResponse(CMonetizeOrder o, Object channelParams) {
        return OrderResponse.builder()
            .orderNo(o.getOrderNo()).userId(o.getUserId())
            .productType(o.getProductType()).productId(o.getProductId())
            .amount(o.getAmount()).status(o.getStatus())
            .paymentNo(o.getPaymentNo()).channelPayParams(channelParams)
            .createdAt(o.getCreatedAt()).expiredAt(o.getExpiredAt()).build();
    }
}
