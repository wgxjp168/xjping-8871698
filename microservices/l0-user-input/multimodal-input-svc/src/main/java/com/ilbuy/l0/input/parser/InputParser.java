package com.ilbuy.l0.input.parser;

import com.ilbuy.l0.input.domain.dto.InputRequest;
import com.ilbuy.l0.input.domain.dto.ParsedInput;
import com.ilbuy.l0.input.domain.enums.InputType;

/**
 * 输入解析器接口（策略模式）
 *
 * <p>每种输入类型对应一个实现：
 * <ul>
 *   <li>{@link TextInputParser}  - 文本</li>
 *   <li>{@link ImageInputParser} - 图片</li>
 *   <li>{@link LinkInputParser}  - 链接</li>
 *   <li>{@link VoiceInputParser} - 语音</li>
 * </ul>
 *
 * @author ILbuy Team
 */
public interface InputParser {

    /**
     * 支持的输入类型
     */
    InputType supportedType();

    /**
     * 解析输入请求为标准化结果
     *
     * @param request 输入请求
     * @return 解析结果（永远不为null，失败时 success=false）
     */
    ParsedInput parse(InputRequest request);
}
