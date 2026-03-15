package com.ilbuy.l0.input.parser;

import com.ilbuy.l0.input.domain.dto.InputRequest;
import com.ilbuy.l0.input.domain.dto.ParsedInput;
import com.ilbuy.l0.input.domain.enums.InputType;
import com.ilbuy.l0.input.service.VoiceToTextService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Component;

/**
 * 语音输入解析器
 *
 * <p>处理流程：
 * <ol>
 *   <li>调用 {@link VoiceToTextService} 将语音转为文本（百度/科大讯飞）</li>
 *   <li>将转写文本交由 {@link TextInputParser} 进行语义解析</li>
 *   <li>在结果中保留 transcribedText 字段供日志审计</li>
 * </ol>
 *
 * @author ILbuy Team
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class VoiceInputParser implements InputParser {

    private final VoiceToTextService voiceToTextService;
    private final TextInputParser    textInputParser;

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

        log.debug("[VoiceParser] 开始语音转文本: url={}, provider={}",
                audioUrl, request.getVoiceProvider());

        try {
            VoiceToTextService.TranscribeResult transcribeResult =
                    voiceToTextService.transcribe(audioUrl, request.getVoiceProvider());

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
            log.info("[VoiceParser] 转写完成: text={}", transcribedText);

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
