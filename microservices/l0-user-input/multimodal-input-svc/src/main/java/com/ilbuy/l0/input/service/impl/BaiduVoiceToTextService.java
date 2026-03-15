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

import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

/**
 * 百度语音识别实现
 *
 * <p>使用百度云语音识别 REST API（短语音，≤60s）：
 * <pre>
 * POST https://vop.baidu.com/server_api
 * Authorization: Bearer ${accessToken}
 * </pre>
 *
 * <p>参考文档：https://ai.baidu.com/ai-doc/SPEECH/Vk38lxily
 *
 * @author ILbuy Team
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class BaiduVoiceToTextService implements VoiceToTextService {

    private static final String PROVIDER_CODE    = "baidu";
    private static final String ASR_URL          = "https://vop.baidu.com/server_api";
    private static final String TOKEN_URL        =
            "https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials";
    private static final int    TIMEOUT_MS       = 10_000;
    private static final int    MAX_AUDIO_BYTES  = 10 * 1024 * 1024; // 10MB

    private final VoiceProviderConfig config;

    @Override
    public String providerCode() {
        return PROVIDER_CODE;
    }

    @Override
    public TranscribeResult transcribe(String audioUrl, String provider) {
        VoiceProviderConfig.BaiduConfig baidu = config.getBaidu();
        if (!baidu.isEnabled()) {
            return TranscribeResult.fail("百度语音识别未启用，请检查配置 ilbuy.voice.baidu.enabled");
        }
        if (StrUtil.isBlank(baidu.getApiKey()) || StrUtil.isBlank(baidu.getSecretKey())) {
            return TranscribeResult.fail("百度语音API Key未配置");
        }

        try {
            long start = System.currentTimeMillis();

            // Step1: 获取 AccessToken
            String accessToken = getAccessToken(baidu.getApiKey(), baidu.getSecretKey());
            if (accessToken == null) {
                return TranscribeResult.fail("获取百度AccessToken失败");
            }

            // Step2: 下载音频并转Base64（实际生产建议流式传输URL）
            byte[] audioData = downloadAudio(audioUrl);
            if (audioData == null || audioData.length == 0) {
                return TranscribeResult.fail("下载音频文件失败: " + audioUrl);
            }
            if (audioData.length > MAX_AUDIO_BYTES) {
                return TranscribeResult.fail("音频文件过大（> 10MB），百度短语音API不支持");
            }

            // Step3: 调用识别API
            String base64Audio = Base64.getEncoder().encodeToString(audioData);
            JSONObject requestBody = JSONUtil.createObj()
                    .set("format", detectAudioFormat(audioUrl))
                    .set("rate", 16000)
                    .set("channel", 1)
                    .set("cuid", "ilbuy-multimodal-svc")
                    .set("token", accessToken)
                    .set("speech", base64Audio)
                    .set("len", audioData.length);

            HttpResponse response = HttpRequest.post(ASR_URL)
                    .header("Content-Type", "application/json")
                    .body(requestBody.toString())
                    .timeout(TIMEOUT_MS)
                    .execute();

            JSONObject result = JSONUtil.parseObj(response.body());
            int errNo = result.getInt("err_no", -1);
            if (errNo != 0) {
                String errMsg = result.getStr("err_msg", "未知错误");
                log.warn("[BaiduASR] 识别失败: err_no={}, msg={}", errNo, errMsg);
                return TranscribeResult.fail("百度语音识别错误(" + errNo + "): " + errMsg);
            }

            String text = result.getJSONArray("result").getStr(0);
            int duration = (int) (System.currentTimeMillis() - start);
            log.info("[BaiduASR] 识别成功: text={}, cost={}ms", text, duration);
            return TranscribeResult.ok(text, duration);

        } catch (Exception e) {
            log.error("[BaiduASR] 调用异常: url={}", audioUrl, e);
            return TranscribeResult.fail("百度语音服务调用失败: " + e.getMessage());
        }
    }

    private String getAccessToken(String apiKey, String secretKey) {
        try {
            String url = TOKEN_URL + "&client_id=" + apiKey + "&client_secret=" + secretKey;
            HttpResponse response = HttpRequest.post(url).timeout(5000).execute();
            JSONObject json = JSONUtil.parseObj(response.body());
            return json.getStr("access_token");
        } catch (Exception e) {
            log.error("[BaiduASR] 获取AccessToken失败", e);
            return null;
        }
    }

    private byte[] downloadAudio(String audioUrl) {
        try {
            return new URL(audioUrl).openStream().readAllBytes();
        } catch (Exception e) {
            log.error("[BaiduASR] 下载音频失败: {}", audioUrl, e);
            return null;
        }
    }

    private String detectAudioFormat(String audioUrl) {
        String lower = audioUrl.toLowerCase();
        if (lower.contains(".mp3")) return "mp3";
        if (lower.contains(".wav")) return "wav";
        if (lower.contains(".pcm")) return "pcm";
        if (lower.contains(".m4a")) return "m4a";
        return "wav"; // 默认
    }
}
