package com.ilbuy.format.client;

import com.ilbuy.format.model.dto.FormatJobRequest;
import com.ilbuy.format.model.entity.FormatJob;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

/**
 * HTTP client for L6 channel-delivery-svc.
 * Triggers multi-channel delivery after format rendering is complete.
 */
@Component
@Slf4j
public class ChannelDeliveryClient {

    private final WebClient webClient;

    public ChannelDeliveryClient(@Value("${l6.channel-delivery-svc.base-url}") String baseUrl,
                                 @Value("${l6.channel-delivery-svc.timeout:30000}") long timeoutMs) {
        this.webClient = WebClient.builder()
                .baseUrl(baseUrl)
                .defaultHeader("X-Internal-Service", "format-output-svc")
                .build();
    }

    /**
     * Trigger delivery for all requested channels with the generated file URLs.
     */
    public void triggerDelivery(FormatJob job, FormatJobRequest request) {
        Map<String, Object> deliveryRequest = new HashMap<>();
        deliveryRequest.put("formatJobNo", job.getFormatJobNo());
        deliveryRequest.put("l5ReportNo", job.getL5ReportNo());
        deliveryRequest.put("userId", job.getUserId());
        deliveryRequest.put("reportTitle", job.getTitle());
        deliveryRequest.put("clientType", job.getClientType());
        deliveryRequest.put("htmlUrl", job.getHtmlUrl());
        deliveryRequest.put("pdfUrl", job.getPdfUrl());
        deliveryRequest.put("excelUrl", job.getExcelUrl());

        // Email delivery
        if (request.isDeliverEmail() && request.getEmailAddress() != null) {
            deliveryRequest.put("deliverEmail", true);
            deliveryRequest.put("emailAddress", request.getEmailAddress());
        }
        // WeChat delivery
        if (request.isDeliverWechat() && request.getWechatOpenId() != null) {
            deliveryRequest.put("deliverWechat", true);
            deliveryRequest.put("wechatOpenId", request.getWechatOpenId());
        }
        // Mobile App push
        if (request.isDeliverApp() && request.getAppDeviceToken() != null) {
            deliveryRequest.put("deliverApp", true);
            deliveryRequest.put("appDeviceToken", request.getAppDeviceToken());
        }
        // Web portal always notified
        deliveryRequest.put("deliverWeb", true);

        try {
            webClient.post()
                    .uri("/internal/v1/deliveries")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(deliveryRequest)
                    .retrieve()
                    .bodyToMono(Map.class)
                    .timeout(Duration.ofSeconds(30))
                    .subscribe(
                            resp -> log.info("[ChannelClient] Delivery triggered for {}", job.getFormatJobNo()),
                            err  -> log.error("[ChannelClient] Delivery failed for {}: {}", job.getFormatJobNo(), err.getMessage())
                    );
        } catch (Exception e) {
            log.error("[ChannelClient] Error triggering delivery: {}", e.getMessage());
        }
    }
}
