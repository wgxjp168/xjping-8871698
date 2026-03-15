package com.ilbuy.l0.input.service;

import lombok.Builder;
import lombok.Data;

/**
 * 语音转文本服务接口
 *
 * <p>实现：
 * <ul>
 *   <li>{@link com.ilbuy.l0.input.service.impl.BaiduVoiceToTextService} - 百度语音识别</li>
 *   <li>{@link com.ilbuy.l0.input.service.impl.IflyVoiceToTextService}  - 科大讯飞语音识别</li>
 * </ul>
 *
 * <p>通过配置 {@code ilbuy.voice.default-provider} 切换默认实现。
 *
 * @author ILbuy Team
 */
public interface VoiceToTextService {

    /**
     * 语音文件转文本
     *
     * @param audioUrl 语音文件OSS地址（支持MP3/WAV/PCM，≤60s）
     * @param provider 指定提供方（baidu/ifly），传null则使用默认配置
     * @return 转写结果
     */
    TranscribeResult transcribe(String audioUrl, String provider);

    /**
     * 提供方标识（baidu / ifly）
     */
    String providerCode();

    @Data
    @Builder
    class TranscribeResult {
        private String  text;
        private boolean success;
        private String  failReason;
        private int     durationMs;

        public static TranscribeResult ok(String text, int durationMs) {
            return TranscribeResult.builder()
                    .text(text).success(true).durationMs(durationMs).build();
        }

        public static TranscribeResult fail(String reason) {
            return TranscribeResult.builder()
                    .success(false).failReason(reason).build();
        }
    }
}
