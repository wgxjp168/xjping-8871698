package com.ilbuy.l0.input.parser;

import com.ilbuy.l0.input.domain.dto.InputRequest;
import com.ilbuy.l0.input.domain.dto.ParsedInput;
import com.ilbuy.l0.input.domain.enums.InputType;
import com.ilbuy.l0.input.service.VoiceToTextService;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * 语音输入解析器
 *
 * <p>处理流程：
 * <ol>
 *   <li>根据请求中的 voiceProvider 字段选择对应 {@link VoiceToTextService} 实现</li>
 *   <li>调用语音转文本（百度/科大讯飞），获取转写文本</li>
 *   <li>将转写文本交由 {@link TextInputParser} 进行语义解析</li>
 *   <li>在结果中保留 transcribedText 字段供日志审计</li>
 * </ol>
 *
 * <p><b>注入策略</b>：注入 {@code Map<String, VoiceToTextService>} 避免多 Bean 二义性，
 * key 为各实现的 {@link VoiceToTextService#providerCode()}（baidu / ifly）。
 *
 * @author ILbuy Team
 */
@Slf4j
@Component
public class VoiceInputParser implements InputParser {

    /** providerCode → VoiceToTextService */
    private final Map<String, VoiceToTextService> voiceServiceMap;
    private final TextInputParser textInputParser;
    private final String defaultProvider;

    public VoiceInputParser(
            java.util.List<VoiceToTextService> voiceServices,
            TextInputParser textInputParser,
            @Value("${ilbuy.voice.default-provider:baidu}") String defaultProvider) {
        this.voiceServiceMap = voiceServices.stream()
                .collect(Collectors.toMap(VoiceToTextService::providerCode, Function.identity()));
        this.textInputParser = textInputParser;
        this.defaultProvider = defaultProvider;
        log.info("[VoiceInputParser] 已注册语音服务: {}, 默认={}", voiceServiceMap.keySet(), defaultProvider);
    }

    @Override
    public InputType supportedType() {
        return InputType.VOICE;
    }

    @Override
    public ParsedInput parse(InputRequest request) {
        String audioUrl = request.getFileUrl();
        if (StringUtils.isBlank(audioUrl)) {
            return ParsedInput.builder()
                    .userId(request.getUserId())
                    .inputType(InputType.VOICE)
                    .success(false)
                    .failReason("语音文件URL不能为空")
                    .build();
        }

        // 根据请求选择语音服务，无效/空时降级到默认服务
        String providerKey = StringUtils.isNotBlank(request.getVoiceProvider())
                ? request.getVoiceProvider() : defaultProvider;
        VoiceToTextService voiceService = voiceServiceMap.getOrDefault(providerKey,
                voiceServiceMap.get(defaultProvider));

        if (voiceService == null) {
            return ParsedInput.builder()
                    .userId(request.getUserId())
                    .inputType(InputType.VOICE)
                    .rawInput(audioUrl)
                    .success(false)
                    .failReason("无可用语音识别服务，请检查配置 ilbuy.voice.baidu.enabled / ifly.enabled")
                    .build();
        }

        log.debug("[VoiceParser] 开始语音转文本: url={}, provider={}", audioUrl, providerKey);

        try {
            VoiceToTextService.TranscribeResult transcribeResult =
                    voiceService.transcribe(audioUrl, providerKey);

            if (!transcribeResult.isSuccess()) {
                return ParsedInput.builder()
                        .userId(request.getUserId())
                        .inputType(InputType.VOICE)
                        .rawInput(audioUrl)
                        .success(false)
                        .failReason("语音转文本失败: " + transcribeResult.getFailReason())
                        .build();
            }

            String transcribedText = transcribeResult.getText();
            log.info("[VoiceParser] 转写完成: provider={}, text={}", providerKey, transcribedText);

            // 将转写文本当作文本输入继续解析
            InputRequest textRequest = new InputRequest();
            textRequest.setInputType(InputType.TEXT);
            textRequest.setTextContent(transcribedText);
            textRequest.setUserId(request.getUserId());

            ParsedInput textResult = textInputParser.parse(textRequest);

            // 覆盖 inputType 为 VOICE，补充 transcribedText 字段
            return ParsedInput.builder()
                    .userId(textResult.getUserId())
                    .inputType(InputType.VOICE)
                    .rawInput(audioUrl)
                    .transcribedText(transcribedText)
                    .productKeyword(textResult.getProductKeyword())
                    .requirement(textResult.getRequirement())
                    .budgetMin(textResult.getBudgetMin())
                    .budgetMax(textResult.getBudgetMax())
                    .success(textResult.isSuccess())
                    .failReason(textResult.getFailReason())
                    .build();

        } catch (Exception e) {
            log.error("[VoiceParser] 语音解析异常: url={}", audioUrl, e);
            return ParsedInput.builder()
                    .userId(request.getUserId())
                    .inputType(InputType.VOICE)
                    .rawInput(audioUrl)
                    .success(false)
                    .failReason("语音服务异常: " + e.getMessage())
                    .build();
        }
    }
}
