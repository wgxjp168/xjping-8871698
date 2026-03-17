package com.ilbuy.bmonetize.service;

import com.ilbuy.bmonetize.domain.*;
import com.ilbuy.bmonetize.domain.BMonetizeOrder.*;
import com.ilbuy.bmonetize.domain.BSaasContract.ContractStatus;
import com.ilbuy.bmonetize.dto.*;
import com.ilbuy.bmonetize.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;

@Service
@RequiredArgsConstructor
@Slf4j
public class BMonetizeService {

    private final BMonetizeOrderRepository orderRepository;
    private final BSaasContractRepository contractRepository;
    private final RestTemplate restTemplate;

    @Value("${ilbuy.gateway.url:http://monetize-gateway-svc:8071}")
    private String gatewayUrl;

    @Transactional
    public BOrderResponse createOrder(CreateBOrderRequest req) {
        String orderNo = "BO-" + UUID.randomUUID().toString().replace("-", "").toUpperCase().substring(0, 16);

        BMonetizeOrder order = BMonetizeOrder.builder()
            .orderNo(orderNo)
            .corpId(req.getCorpId())
            .contactUserId(req.getContactUserId())
            .productType(req.getProductType())
            .productId(req.getProductId())
            .amount(req.getAmount())
            .status(OrderStatus.PENDING_PAYMENT)
            .build();
        orderRepository.save(order);

        // Call payment gateway
        Map<String, Object> gatewayReq = new HashMap<>();
        gatewayReq.put("bizOrderNo", orderNo);
        gatewayReq.put("userId", req.getContactUserId());
        gatewayReq.put("amount", req.getAmount());
        gatewayReq.put("channel", req.getPaymentChannel());
        gatewayReq.put("bizType", req.getProductType() == ProductType.SAAS_ANNUAL ? "B_SAAS" :
                                    req.getProductType() == ProductType.API_CALL ? "B_API" : "B_CUSTOM");
        gatewayReq.put("subject", "ILbuy企业版 - " + req.getProductId());
        if (req.getChannelUserId() != null) gatewayReq.put("channelUserId", req.getChannelUserId());

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
            log.error("[BMonetize] Gateway call failed: {}", e.getMessage());
        }

        log.info("[BMonetize] Order created: orderNo={}, corpId={}, amount={}", orderNo, req.getCorpId(), req.getAmount());
        return buildOrderResponse(order, channelParams);
    }

    @Transactional
    public void confirmPayment(String paymentNo, String bizOrderNo) {
        BMonetizeOrder order = orderRepository.findByOrderNo(bizOrderNo)
            .orElseGet(() -> orderRepository.findByPaymentNo(paymentNo).orElse(null));
        if (order == null || order.getStatus() == OrderStatus.PAID) return;

        order.setStatus(OrderStatus.PAID);
        order.setPaymentNo(paymentNo);
        order.setPaidAt(LocalDateTime.now());
        orderRepository.save(order);

        // Activate SaaS contract if applicable
        if (order.getProductType() == ProductType.SAAS_ANNUAL) {
            activateSaasContract(order);
        }
        log.info("[BMonetize] Order confirmed: orderNo={}", order.getOrderNo());
    }

    private void activateSaasContract(BMonetizeOrder order) {
        // Expire old contract if any
        contractRepository.findByCorpIdAndStatus(order.getCorpId(), ContractStatus.ACTIVE)
            .ifPresent(old -> {
                old.setStatus(ContractStatus.EXPIRED);
                contractRepository.save(old);
            });

        String contractNo = "CTR-" + UUID.randomUUID().toString().replace("-", "").toUpperCase().substring(0, 16);
        BSaasContract contract = BSaasContract.builder()
            .contractNo(contractNo)
            .corpId(order.getCorpId())
            .planCode(order.getProductId())
            .annualFee(order.getAmount())
            .apiCallLimit(100_000L)   // default quota; override by plan
            .startDate(LocalDate.now())
            .endDate(LocalDate.now().plusYears(1))
            .status(ContractStatus.ACTIVE)
            .orderNo(order.getOrderNo())
            .build();
        contractRepository.save(contract);
        order.setContractNo(contractNo);
        orderRepository.save(order);
        log.info("[BMonetize] SaaS contract activated: contractNo={}, corpId={}", contractNo, order.getCorpId());
    }

    @Transactional(readOnly = true)
    public Optional<BSaasContract> getActiveContract(Long corpId) {
        return contractRepository.findByCorpIdAndStatus(corpId, ContractStatus.ACTIVE);
    }

    @Transactional(readOnly = true)
    public BOrderResponse getOrder(String orderNo) {
        return buildOrderResponse(orderRepository.findByOrderNo(orderNo)
            .orElseThrow(() -> new IllegalArgumentException("Order not found: " + orderNo)), null);
    }

    @Scheduled(cron = "0 0 2 * * *")
    @Transactional
    public void expireContracts() {
        contractRepository.findAll().stream()
            .filter(c -> c.getStatus() == ContractStatus.ACTIVE && LocalDate.now().isAfter(c.getEndDate()))
            .forEach(c -> {
                c.setStatus(ContractStatus.EXPIRED);
                contractRepository.save(c);
                log.info("[BMonetize] Contract expired: {}", c.getContractNo());
            });
    }

    private BOrderResponse buildOrderResponse(BMonetizeOrder o, Object channelParams) {
        return BOrderResponse.builder()
            .orderNo(o.getOrderNo()).corpId(o.getCorpId())
            .productType(o.getProductType()).productId(o.getProductId())
            .amount(o.getAmount()).status(o.getStatus())
            .paymentNo(o.getPaymentNo()).contractNo(o.getContractNo())
            .channelPayParams(channelParams).createdAt(o.getCreatedAt()).build();
    }
}
