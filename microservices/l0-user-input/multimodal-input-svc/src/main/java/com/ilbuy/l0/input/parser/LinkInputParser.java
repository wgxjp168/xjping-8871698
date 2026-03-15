package com.ilbuy.l0.input.parser;

import com.ilbuy.l0.input.domain.dto.InputRequest;
import com.ilbuy.l0.input.domain.dto.ParsedInput;
import com.ilbuy.l0.input.domain.enums.InputType;
import com.ilbuy.l0.input.parser.platform.EcommercePlatform;
import com.ilbuy.l0.input.parser.platform.PlatformUrlParser;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Component;

/**
 * 链接输入解析器
 *
 * <p>解析7大电商平台商品链接，提取平台标识、商品ID和标准化URL。
 * 实际商品名称/描述由 L3 数据采集层爬取后回填。
 *
 * @author ILbuy Team
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class LinkInputParser implements InputParser {

    private final PlatformUrlParser platformUrlParser;

    @Override
    public InputType supportedType() {
        return InputType.LINK;
    }

    @Override
    public ParsedInput parse(InputRequest request) {
        String url = request.getRawUrl();
        if (StringUtils.isBlank(url)) {
            return ParsedInput.builder()
                    .userId(request.getUserId())
                    .inputType(InputType.LINK)
                    .success(false)
                    .failReason("链接URL不能为空")
                    .build();
        }

        log.debug("[LinkParser] 解析链接: {}", url);

        PlatformUrlParser.ParseResult result = platformUrlParser.parse(url);

        if (!result.isSuccess()) {
            log.warn("[LinkParser] 平台识别失败: {}, reason={}", url, result.getFailReason());
            return ParsedInput.builder()
                    .userId(request.getUserId())
                    .inputType(InputType.LINK)
                    .rawInput(url)
                    .platform(EcommercePlatform.UNKNOWN)
                    .normalizedUrl(url)
                    .success(false)
                    .failReason("无法识别的电商平台: " + result.getFailReason())
                    .build();
        }

        log.info("[LinkParser] 解析成功: platform={}, productId={}, url={}",
                result.getPlatform(), result.getProductId(), result.getNormalizedUrl());

        return ParsedInput.builder()
                .userId(request.getUserId())
                .inputType(InputType.LINK)
                .rawInput(url)
                .platform(result.getPlatform())
                .platformProductId(result.getProductId())
                .normalizedUrl(result.getNormalizedUrl())
                // productKeyword 和 requirement 由 L3 数据采集后回填
                .productKeyword(buildTempKeyword(result.getPlatform(), result.getProductId()))
                .requirement("来自" + result.getPlatform().getDisplayName() + "的商品链接")
                .success(true)
                .build();
    }

    private String buildTempKeyword(EcommercePlatform platform, String productId) {
        // 临时关键词，待L3采集后覆盖
        if (productId != null) {
            return platform.getDisplayName() + "商品#" + productId;
        }
        return platform.getDisplayName() + "商品";
    }
}
