package com.ilbuy.l0.input.parser;

import com.ilbuy.l0.input.domain.dto.InputRequest;
import com.ilbuy.l0.input.domain.dto.ParsedInput;
import com.ilbuy.l0.input.domain.enums.InputType;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 文本输入解析器
 *
 * <p>解析用户输入的自然语言文本，提取：
 * <ul>
 *   <li>商品关键词（去除口语化表达）</li>
 *   <li>预算范围（识别"5000元以内"/"3000-5000元"等模式）</li>
 *   <li>标准化需求文本</li>
 * </ul>
 *
 * <p>当前为基于规则的轻量实现；生产环境建议对接 L2 意图识别服务增强精度。
 *
 * @author ILbuy Team
 */
@Slf4j
@Component
public class TextInputParser implements InputParser {

    // 预算区间：3000-5000元
    private static final Pattern BUDGET_RANGE_PATTERN =
            Pattern.compile("([0-9]+(?:\\.[0-9]+)?)\\s*[-~到至]\\s*([0-9]+(?:\\.[0-9]+)?)\\s*[元万块]");

    // 预算上限：5000元以内/5000元左右/5000元以下
    private static final Pattern BUDGET_MAX_PATTERN =
            Pattern.compile("([0-9]+(?:\\.[0-9]+)?)\\s*[元万块]?\\s*(?:以内|左右|以下|不超过|之内)");

    // 预算带万字：1万/2.5万
    private static final Pattern BUDGET_WAN_PATTERN =
            Pattern.compile("([0-9]+(?:\\.[0-9]+)?)\\s*万\\s*(?:元|块)?\\s*(?:以内|左右|以下|不超过)?");

    // 商品关键词（去除意向词后的核心名词）
    private static final Pattern[] INTENT_PREFIXES = {
            Pattern.compile("^(?:我想买|我要买|帮我看看|推荐一个|找一款|买个|想要|要买)\\s*"),
            Pattern.compile("^(?:一台|一个|一款|一件|一双|一套)\\s*"),
    };

    @Override
    public InputType supportedType() {
        return InputType.TEXT;
    }

    @Override
    public ParsedInput parse(InputRequest request) {
        String text = request.getTextContent();
        if (StringUtils.isBlank(text)) {
            return ParsedInput.builder()
                    .userId(request.getUserId())
                    .inputType(InputType.TEXT)
                    .success(false)
                    .failReason("文本内容不能为空")
                    .build();
        }

        text = text.trim();
        log.debug("[TextParser] 解析文本: {}", text);

        BigDecimal[] budget = extractBudget(text);
        String keyword = extractKeyword(text);

        return ParsedInput.builder()
                .userId(request.getUserId())
                .inputType(InputType.TEXT)
                .rawInput(text)
                .productKeyword(keyword)
                .requirement(text)
                .budgetMin(budget[0])
                .budgetMax(budget[1])
                .success(true)
                .build();
    }

    /**
     * 提取预算区间 [min, max]，无法识别时返回 [null, null]
     */
    BigDecimal[] extractBudget(String text) {
        // 先匹配区间：3000-5000元
        Matcher rangeMatcher = BUDGET_RANGE_PATTERN.matcher(text);
        if (rangeMatcher.find()) {
            BigDecimal min = parseMoney(rangeMatcher.group(1), text);
            BigDecimal max = parseMoney(rangeMatcher.group(2), text);
            return new BigDecimal[]{min, max};
        }

        // 匹配万单位：1.5万以内
        Matcher wanMatcher = BUDGET_WAN_PATTERN.matcher(text);
        if (wanMatcher.find()) {
            BigDecimal amount = new BigDecimal(wanMatcher.group(1))
                    .multiply(BigDecimal.valueOf(10000));
            return new BigDecimal[]{null, amount};
        }

        // 匹配上限：5000元以内
        Matcher maxMatcher = BUDGET_MAX_PATTERN.matcher(text);
        if (maxMatcher.find()) {
            BigDecimal max = parseMoney(maxMatcher.group(1), text);
            return new BigDecimal[]{null, max};
        }

        return new BigDecimal[]{null, null};
    }

    private BigDecimal parseMoney(String numStr, String originalText) {
        try {
            return new BigDecimal(numStr);
        } catch (NumberFormatException e) {
            log.warn("[TextParser] 预算数字解析失败: {} in {}", numStr, originalText);
            return null;
        }
    }

    /**
     * 提取商品关键词（去除意向前缀和量词）
     */
    String extractKeyword(String text) {
        String keyword = text;
        // 逐步去除意向词前缀
        for (Pattern prefix : INTENT_PREFIXES) {
            keyword = prefix.matcher(keyword).replaceFirst("");
        }
        // 截取预算描述前的内容
        int budgetIdx = findBudgetIndex(keyword);
        if (budgetIdx > 3) {
            keyword = keyword.substring(0, budgetIdx).trim();
        }
        return keyword.isBlank() ? text : keyword;
    }

    private int findBudgetIndex(String text) {
        // 找到第一个数字+元/万的位置
        Matcher m = Pattern.compile("[0-9]+\\s*(?:元|万|块)").matcher(text);
        return m.find() ? m.start() : text.length();
    }
}
