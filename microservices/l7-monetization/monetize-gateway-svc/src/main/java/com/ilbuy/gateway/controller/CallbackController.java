package com.ilbuy.gateway.controller;

import com.ilbuy.gateway.service.PaymentGatewayService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Payment channel callback endpoints.
 * URLs must be whitelisted in SecurityConfig.
 */
@RestController
@RequestMapping("/api/v1/payments")
@RequiredArgsConstructor
@Slf4j
public class CallbackController {

    private final PaymentGatewayService paymentGatewayService;

    @PostMapping(value = "/wechat/notify", produces = MediaType.TEXT_XML_VALUE)
    public String wechatNotify(HttpServletRequest request) {
        log.info("[Callback] WeChat Pay callback received");
        try {
            String rawBody = new BufferedReader(new InputStreamReader(request.getInputStream(), StandardCharsets.UTF_8))
                .lines().collect(Collectors.joining());
            Map<String, String> params = parseWechatXml(rawBody);
            String result = paymentGatewayService.handleCallback("WECHAT", params, rawBody);
            return result.equals("SUCCESS")
                ? "<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>"
                : "<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[ERROR]]></return_msg></xml>";
        } catch (Exception e) {
            log.error("[Callback] WeChat notify error: {}", e.getMessage());
            return "<xml><return_code><![CDATA[FAIL]]></return_code></xml>";
        }
    }

    @PostMapping("/alipay/notify")
    public String alipayNotify(HttpServletRequest request) {
        log.info("[Callback] Alipay callback received");
        Map<String, String> params = new HashMap<>();
        request.getParameterMap().forEach((k, v) -> params.put(k, v[0]));
        String result = paymentGatewayService.handleCallback("ALIPAY", params, params.toString());
        return result;
    }

    private Map<String, String> parseWechatXml(String xml) {
        Map<String, String> map = new HashMap<>();
        // Simple XML parsing for WeChat Pay notification
        java.util.regex.Pattern p = java.util.regex.Pattern.compile("<(\\w+)><!\\[CDATA\\[(.+?)\\]\\]><\\/\\1>|<(\\w+)>([^<]*)<\\/\\3>");
        java.util.regex.Matcher m = p.matcher(xml);
        while (m.find()) {
            if (m.group(1) != null) map.put(m.group(1), m.group(2));
            else if (m.group(3) != null) map.put(m.group(3), m.group(4));
        }
        return map;
    }
}
