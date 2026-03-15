package com.ilbuy.l0.input.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * 语音识别提供方配置
 *
 * <p>YAML示例：
 * <pre>
 * ilbuy:
 *   voice:
 *     default-provider: baidu
 *     baidu:
 *       enabled: true
 *       api-key: "your-api-key"
 *       secret-key: "your-secret-key"
 *     ifly:
 *       enabled: false
 *       app-id: "your-app-id"
 *       api-key: "your-api-key"
 * </pre>
 *
 * @author ILbuy Team
 */
@Data
@Component
@ConfigurationProperties(prefix = "ilbuy.voice")
public class VoiceProviderConfig {

    /** 默认语音识别提供方（baidu / ifly） */
    private String defaultProvider = "baidu";

    private BaiduConfig baidu = new BaiduConfig();
    private IflyConfig  ifly  = new IflyConfig();

    @Data
    public static class BaiduConfig {
        private boolean enabled   = false;
        private String  apiKey    = "";
        private String  secretKey = "";
    }

    @Data
    public static class IflyConfig {
        private boolean enabled = false;
        private String  appId   = "";
        private String  apiKey  = "";
        private String  apiSecret = "";
    }
}
