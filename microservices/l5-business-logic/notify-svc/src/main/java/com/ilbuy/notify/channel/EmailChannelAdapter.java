package com.ilbuy.notify.channel;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * Mock email channel adapter.
 * In production, this would use Spring Mail / JavaMailSender or an email API (e.g., SendGrid).
 */
@Component
@Slf4j
public class EmailChannelAdapter {

    /**
     * Send an email message.
     *
     * @param email   recipient email address
     * @param subject email subject
     * @param content email body
     */
    public void send(String email, String subject, String content) {
        log.info("Email sent to {}: {}", email, subject);
    }
}
