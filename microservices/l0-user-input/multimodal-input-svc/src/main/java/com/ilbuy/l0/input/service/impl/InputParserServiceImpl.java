package com.ilbuy.l0.input.service.impl;

import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.common.core.result.ResultCode;
import com.ilbuy.l0.input.domain.dto.InputRequest;
import com.ilbuy.l0.input.domain.dto.ParsedInput;
import com.ilbuy.l0.input.domain.enums.InputType;
import com.ilbuy.l0.input.parser.InputParser;
import com.ilbuy.l0.input.service.InputParserService;
import com.ilbuy.l0.input.service.VoiceToTextService;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * 输入解析编排服务实现
 *
 * <p>基于策略模式，将解析请求分发到对应的 {@link InputParser} 实现。
 * 对语音输入支持按 voiceProvider 动态切换百度/讯飞。
 *
 * @author ILbuy Team
 */
@Slf4j
@Service
public class InputParserServiceImpl implements InputParserService {

    /** inputType → Parser 映射（Spring自动注入所有InputParser实现）*/
    private final Map<InputType, InputParser> parserMap;

    /** voiceProvider → VoiceToTextService 映射 */
    private final Map<String, VoiceToTextService> voiceServiceMap;

    private final String defaultVoiceProvider;

    public InputParserServiceImpl(
            List<InputParser> parsers,
            List<VoiceToTextService> voiceServices,
            @org.springframework.beans.factory.annotation.Value(
                    "${ilbuy.voice.default-provider:baidu}") String defaultVoiceProvider) {

        this.parserMap = parsers.stream()
                .collect(Collectors.toMap(InputParser::supportedType, Function.identity()));
        this.voiceServiceMap = voiceServices.stream()
                .collect(Collectors.toMap(VoiceToTextService::providerCode, Function.identity()));
        this.defaultVoiceProvider = defaultVoiceProvider;

        log.info("[InputParserService] 已注册解析器: {}", parserMap.keySet());
        log.info("[InputParserService] 已注册语音服务: {}, 默认={}",
                voiceServiceMap.keySet(), defaultVoiceProvider);
    }

    @Override
    public ParsedInput parse(InputRequest request) {
        validateRequest(request);

        InputType type = request.getInputType();
        InputParser parser = parserMap.get(type);

        if (parser == null) {
            throw new BizException(ResultCode.BAD_REQUEST.getCode(),
                    "不支持的输入类型: " + type);
        }

        log.info("[InputParserService] 开始解析: type={}, userId={}", type, request.getUserId());
        ParsedInput result = parser.parse(request);

        log.info("[InputParserService] 解析完成: type={}, success={}, keyword={}",
                type, result.isSuccess(), result.getProductKeyword());

        return result;
    }

    @Override
    public List<ParsedInput> parseBatch(List<InputRequest> requests) {
        if (requests == null || requests.isEmpty()) {
            throw new BizException(ResultCode.BAD_REQUEST.getCode(), "批量解析请求不能为空");
        }
        if (requests.size() > 10) {
            throw new BizException(ResultCode.BAD_REQUEST.getCode(), "批量解析最多10条");
        }

        return requests.stream()
                .map(req -> {
                    try {
                        return parse(req);
                    } catch (Exception e) {
                        log.warn("[InputParserService] 批量解析单条失败", e);
                        return ParsedInput.builder()
                                .inputType(req.getInputType())
                                .userId(req.getUserId())
                                .success(false)
                                .failReason(e.getMessage())
                                .build();
                    }
                })
                .collect(Collectors.toList());
    }

    private void validateRequest(InputRequest request) {
        if (request == null) {
            throw new BizException(ResultCode.BAD_REQUEST.getCode(), "请求不能为null");
        }
        if (request.getInputType() == null) {
            throw new BizException(ResultCode.BAD_REQUEST.getCode(), "inputType不能为空");
        }
        // 各类型必填字段校验
        switch (request.getInputType()) {
            case TEXT  -> { if (StringUtils.isBlank(request.getTextContent()))
                throw new BizException(ResultCode.BAD_REQUEST.getCode(), "文本内容不能为空"); }
            case LINK  -> { if (StringUtils.isBlank(request.getRawUrl()))
                throw new BizException(ResultCode.BAD_REQUEST.getCode(), "链接URL不能为空"); }
            case IMAGE, VOICE -> { if (StringUtils.isBlank(request.getFileUrl()))
                throw new BizException(ResultCode.BAD_REQUEST.getCode(), "文件URL不能为空"); }
        }
    }
}
