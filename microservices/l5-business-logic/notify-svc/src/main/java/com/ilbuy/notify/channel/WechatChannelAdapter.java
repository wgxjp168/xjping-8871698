package com.ilbuy.notify.channel;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * Mock WeChat template message channel adapter.
 * In production, this would call the WeChat MP (公众号) or Mini Program template message API.
 */
@Component
@Slf4j
public class WechatChannelAdapter {

    /**
     * Send a WeChat template message to the given openId.
     *
     * @param openId   recipient WeChat openId
     * @param templateId WeChat template ID
     * @param content  rendered content / data map
     */
    public void send(String openId, String templateId, String content) {
        log.info("WeChat template msg sent to {}", openId);
    }
}
