package com.ilbuy.l0.input.service.impl;

import cn.hutool.core.util.StrUtil;
import cn.hutool.http.HttpRequest;
import cn.hutool.http.HttpResponse;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import com.ilbuy.l0.input.config.VoiceProviderConfig;
import com.ilbuy.l0.input.service.VoiceToTextService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * 科大讯飞语音识别实现（REST API）
 *
 * <p>使用讯飞开放平台短语音识别 REST API：
 * <pre>
 * POST https://iat.xfyun.cn/v1/service/v1/iat
 * </pre>
 *
 * <p>签名方式：HMAC-SHA256（X-CurTime + X-Param + APIKey）
 * 参考文档：https://www.xfyun.cn/doc/asr/voicedictation/API.html
 *
 * @author ILbuy Team
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class IflyVoiceToTextService implements VoiceToTextService {

    private static final String PROVIDER_CODE = "ifly";
    private static final String ASR_URL       = "https://iat.xfyun.cn/v1/service/v1/iat";
    private static final int    TIMEOUT_MS    = 15_000;

    private final VoiceProviderConfig config;

    @Override
    public String providerCode() {
        return PROVIDER_CODE;
    }

    @Override
    public TranscribeResult transcribe(String audioUrl, String provider) {
        VoiceProviderConfig.IflyConfig ifly = config.getIfly();
        if (!ifly.isEnabled()) {
            return TranscribeResult.fail("讯飞语音识别未启用，请检查配置 ilbuy.voice.ifly.enabled");
        }
        if (StrUtil.isBlank(ifly.getAppId()) || StrUtil.isBlank(ifly.getApiKey())) {
            return TranscribeResult.fail("讯飞语音 AppId/ApiKey 未配置");
        }

        try {
            long start = System.currentTimeMillis();

            // 下载音频
            byte[] audioData = downloadAudio(audioUrl);
            if (audioData == null || audioData.length == 0) {
                return TranscribeResult.fail("下载音频文件失败: " + audioUrl);
            }

            // 构建请求参数
            String curTime = String.valueOf(System.currentTimeMillis() / 1000);
            String paramJson = buildParamJson(detectFormat(audioUrl));
            String paramBase64 = Base64.getEncoder()
                    .encodeToString(paramJson.getBytes(StandardCharsets.UTF_8));
            String checkSum = buildCheckSum(ifly.getApiKey(), curTime, paramBase64);
            String audioBase64 = Base64.getEncoder().encodeToString(audioData);

            HttpResponse response = HttpRequest.post(ASR_URL)
                    .header("X-Appid", ifly.getAppId())
                    .header("X-CurTime", curTime)
                    .header("X-Param", paramBase64)
                    .header("X-CheckSum", checkSum)
                    .header("Content-Type", "application/x-www-form-urlencoded")
                    .form("audio", audioBase64)
                    .timeout(TIMEOUT_MS)
                    .execute();

            JSONObject result = JSONUtil.parseObj(response.body());
            String code = result.getStr("code", "-1");
            if (!"0".equals(code)) {
                String desc = result.getStr("desc", "未知错误");
                log.warn("[IflyASR] 识别失败: code={}, desc={}", code, desc);
                return TranscribeResult.fail("讯飞语音识别错误(" + code + "): " + desc);
            }

            // 解析讯飞 ws 结果格式
            String text = parseIflyResult(result);
            int duration = (int) (System.currentTimeMillis() - start);
            log.info("[IflyASR] 识别成功: text={}, cost={}ms", text, duration);
            return TranscribeResult.ok(text, duration);

        } catch (Exception e) {
            log.error("[IflyASR] 调用异常: url={}", audioUrl, e);
            return TranscribeResult.fail("讯飞语音服务调用失败: " + e.getMessage());
        }
    }

    private String parseIflyResult(JSONObject response) {
        try {
            // 讯飞返回格式: data.result.ws[].cw[].w
            StringBuilder sb = new StringBuilder();
            response.getJSONObject("data")
                    .getJSONObject("result")
                    .getJSONArray("ws")
                    .forEach(ws -> {
                        JSONObject wsObj = (JSONObject) ws;
                        wsObj.getJSONArray("cw").forEach(cw -> {
                            sb.append(((JSONObject) cw).getStr("w", ""));
                        });
                    });
            return sb.toString();
        } catch (Exception e) {
            log.warn("[IflyASR] 解析响应结构失败", e);
            return response.getStr("data", "");
        }
    }

    private String buildParamJson(String format) {
        return JSONUtil.createObj()
                .set("engine_type", "sms16k")
                .set("aue", format)
                .set("language", "zh_cn")
                .set("accent", "mandarin")
                .toString();
    }

    private String buildCheckSum(String apiKey, String curTime, String param) throws Exception {
        String raw = apiKey + curTime + param;
        Mac mac = Mac.getInstance("HmacMD5");
        mac.init(new SecretKeySpec(apiKey.getBytes(StandardCharsets.UTF_8), "HmacMD5"));
        byte[] digest = mac.doFinal(raw.getBytes(StandardCharsets.UTF_8));
        StringBuilder hex = new StringBuilder();
        for (byte b : digest) {
            hex.append(String.format("%02x", b));
        }
        return hex.toString();
    }

    private byte[] downloadAudio(String audioUrl) {
        try {
            return new URL(audioUrl).openStream().readAllBytes();
        } catch (Exception e) {
            log.error("[IflyASR] 下载音频失败: {}", audioUrl, e);
            return null;
        }
    }

    private String detectFormat(String audioUrl) {
        String lower = audioUrl.toLowerCase();
        if (lower.contains(".mp3")) return "lame";
        if (lower.contains(".pcm")) return "raw";
        return "raw"; // 默认PCM
    }
}
