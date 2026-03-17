package com.ilbuy.datamonetize.service;

import com.ilbuy.datamonetize.domain.DataOrder;
import com.ilbuy.datamonetize.domain.DataOrder.OrderStatus;
import com.ilbuy.datamonetize.domain.DataProduct;
import com.ilbuy.datamonetize.dto.CreateDataOrderRequest;
import com.ilbuy.datamonetize.dto.DataOrderResponse;
import com.ilbuy.datamonetize.repository.DataOrderRepository;
import com.ilbuy.datamonetize.repository.DataProductRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
@Transactional
public class DataMonetizeService {

    private final DataOrderRepository orderRepository;
    private final DataProductRepository productRepository;
    private final RestTemplate restTemplate;

    @Value("${ilbuy.gateway.url:http://monetize-gateway-svc:8071}")
    private String gatewayUrl;

    @Value("${ilbuy.l6.report.url:http://report-generator-svc:8061}")
    private String reportUrl;

    public DataOrderResponse createOrder(CreateDataOrderRequest req) {
        DataProduct product = productRepository.findByProductCodeAndEnabled(req.getProductCode(), true)
            .orElseThrow(() -> new IllegalArgumentException("Product not found or disabled: " + req.getProductCode()));

        int qty = req.getQuantity() != null ? req.getQuantity() : 1;
        BigDecimal totalAmount = product.getUnitPrice().multiply(BigDecimal.valueOf(qty));

        String orderNo = "DO-" + UUID.randomUUID().toString().replace("-", "").toUpperCase().substring(0, 16);

        DataOrder order = DataOrder.builder()
            .orderNo(orderNo)
            .userId(req.getUserId())
            .corpId(req.getCorpId())
            .productCode(product.getProductCode())
            .productName(product.getName())
            .unitPrice(product.getUnitPrice())
            .quantity(qty)
            .totalAmount(totalAmount)
            .status(OrderStatus.PENDING_PAYMENT)
            .build();
        orderRepository.save(order);

        // Call payment gateway
        Map<String, Object> gatewayReq = new HashMap<>();
        gatewayReq.put("bizOrderNo", orderNo);
        gatewayReq.put("userId", req.getUserId());
        gatewayReq.put("amount", totalAmount);
        gatewayReq.put("channel", req.getPaymentChannel());
        gatewayReq.put("bizType", "DATA_MONETIZE");
        gatewayReq.put("subject", "ILbuy数据产品 - " + product.getName());
        if (req.getChannelUserId() != null) {
            gatewayReq.put("channelUserId", req.getChannelUserId());
        }

        Object channelParams = null;
        String paymentNo = null;
        try {
            ResponseEntity<Map> resp = restTemplate.postForEntity(gatewayUrl + "/api/v1/payments", gatewayReq, Map.class);
            if (resp.getStatusCode() == HttpStatus.OK && resp.getBody() != null) {
                paymentNo = (String) resp.getBody().get("paymentNo");
                channelParams = resp.getBody().get("channelPayParams");
                order.setPaymentNo(paymentNo);
                orderRepository.save(order);
            }
        } catch (Exception e) {
            log.error("[DataMonetize] Gateway call failed: {}", e.getMessage());
        }

        log.info("[DataMonetize] Order created: orderNo={}, userId={}, productCode={}, totalAmount={}",
            orderNo, req.getUserId(), req.getProductCode(), totalAmount);
        return buildOrderResponse(order, channelParams);
    }

    public void confirmPayment(String paymentNo, String bizOrderNo) {
        DataOrder order = orderRepository.findByOrderNo(bizOrderNo)
            .orElseGet(() -> orderRepository.findByPaymentNo(paymentNo).orElse(null));
        if (order == null || order.getStatus() == OrderStatus.PAID) {
            return;
        }

        order.setStatus(OrderStatus.PAID);
        order.setPaymentNo(paymentNo);
        order.setPaidAt(LocalDateTime.now());
        orderRepository.save(order);

        // Call L6 report endpoint if product is MARKET_REPORT category
        triggerReportJobIfApplicable(order);

        log.info("[DataMonetize] Payment confirmed: orderNo={}, paymentNo={}", order.getOrderNo(), paymentNo);
    }

    private void triggerReportJobIfApplicable(DataOrder order) {
        try {
            DataProduct product = productRepository.findByProductCodeAndEnabled(order.getProductCode(), true)
                .orElse(null);
            if (product != null && "MARKET_REPORT".equals(product.getCategory())) {
                Map<String, Object> reportReq = new HashMap<>();
                reportReq.put("orderNo", order.getOrderNo());
                reportReq.put("userId", order.getUserId());
                reportReq.put("productCode", order.getProductCode());
                ResponseEntity<Map> resp = restTemplate.postForEntity(
                    reportUrl + "/api/v1/report-jobs", reportReq, Map.class);
                if (resp.getStatusCode() == HttpStatus.OK && resp.getBody() != null) {
                    String reportJobNo = (String) resp.getBody().get("jobNo");
                    order.setReportJobNo(reportJobNo);
                    orderRepository.save(order);
                    log.info("[DataMonetize] Report job triggered: reportJobNo={}, orderNo={}", reportJobNo, order.getOrderNo());
                }
            }
        } catch (Exception e) {
            log.warn("[DataMonetize] Failed to trigger report job for orderNo={}: {}", order.getOrderNo(), e.getMessage());
        }
    }

    public void fulfillOrder(String orderNo) {
        DataOrder order = orderRepository.findByOrderNo(orderNo)
            .orElseThrow(() -> new IllegalArgumentException("Order not found: " + orderNo));
        order.setStatus(OrderStatus.FULFILLED);
        orderRepository.save(order);
        log.info("[DataMonetize] Order fulfilled: orderNo={}", orderNo);
    }

    @Transactional(readOnly = true)
    public DataOrderResponse getOrder(String orderNo) {
        DataOrder order = orderRepository.findByOrderNo(orderNo)
            .orElseThrow(() -> new IllegalArgumentException("Order not found: " + orderNo));
        return buildOrderResponse(order, null);
    }

    @Transactional(readOnly = true)
    public List<DataProduct> getAvailableProducts() {
        return productRepository.findAllByEnabledTrue();
    }

    private DataOrderResponse buildOrderResponse(DataOrder o, Object channelParams) {
        return DataOrderResponse.builder()
            .orderNo(o.getOrderNo())
            .userId(o.getUserId())
            .corpId(o.getCorpId())
            .productCode(o.getProductCode())
            .productName(o.getProductName())
            .unitPrice(o.getUnitPrice())
            .quantity(o.getQuantity())
            .totalAmount(o.getTotalAmount())
            .status(o.getStatus())
            .paymentNo(o.getPaymentNo())
            .channelPayParams(channelParams)
            .createdAt(o.getCreatedAt())
            .build();
    }
}
