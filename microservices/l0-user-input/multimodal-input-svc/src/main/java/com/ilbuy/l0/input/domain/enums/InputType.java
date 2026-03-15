package com.ilbuy.l0.input.domain.enums;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import lombok.Getter;
import lombok.RequiredArgsConstructor;

/**
 * 用户输入类型枚举
 *
 * <p>定义 L0 层支持的四种输入模态：
 * <ul>
 *   <li>{@link #TEXT}   - 文本输入（商品名称/描述/需求）</li>
 *   <li>{@link #IMAGE}  - 图片输入（拍照识别商品）</li>
 *   <li>{@link #LINK}   - 链接输入（电商平台商品URL）</li>
 *   <li>{@link #VOICE}  - 语音输入（语音转文本后再解析）</li>
 * </ul>
 *
 * @author ILbuy Team
 */
@Getter
@RequiredArgsConstructor
public enum InputType {

    TEXT("text", "文本输入"),
    IMAGE("image", "图片输入"),
    LINK("link", "链接输入"),
    VOICE("voice", "语音输入");

    @JsonValue
    private final String code;
    private final String description;

    @JsonCreator
    public static InputType fromCode(String code) {
        if (code == null) return TEXT;
        for (InputType type : values()) {
            if (type.code.equalsIgnoreCase(code)) {
                return type;
            }
        }
        return TEXT;
    }
}
