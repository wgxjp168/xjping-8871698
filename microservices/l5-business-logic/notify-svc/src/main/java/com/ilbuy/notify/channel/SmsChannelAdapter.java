package com.ilbuy.notify.channel;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * Mock SMS channel adapter.
 * In production, this would integrate with an SMS gateway (e.g., Alibaba Cloud SMS, Tencent Cloud SMS).
 */
@Component
@Slf4j
public class SmsChannelAdapter {

    /**
     * Send an SMS message to the given phone number.
     *
     * @param phone   recipient phone number
     * @param content SMS content
     */
    public void send(String phone, String content) {
        log.info("SMS sent to {}: {}", phone, content);
    }
}
