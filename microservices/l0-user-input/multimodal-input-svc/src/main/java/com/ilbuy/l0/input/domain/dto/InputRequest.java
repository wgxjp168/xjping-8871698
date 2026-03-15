package com.ilbuy.l0.input.domain.dto;

import com.ilbuy.l0.input.domain.enums.InputType;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * 多模态输入请求 DTO
 *
 * <p>根据 inputType 的不同，填写对应字段：
 * <ul>
 *   <li>TEXT  → textContent</li>
 *   <li>IMAGE → fileUrl（OSS地址）或 base64Content</li>
 *   <li>LINK  → rawUrl</li>
 *   <li>VOICE → fileUrl（OSS音频地址）</li>
 * </ul>
 *
 * @author ILbuy Team
 */
@Data
@Schema(description = "多模态输入请求")
public class InputRequest {

    @NotNull(message = "输入类型不能为空")
    @Schema(description = "输入类型", example = "text", requiredMode = Schema.RequiredMode.REQUIRED)
    private InputType inputType;

    @Schema(description = "文本内容（inputType=text时必填）", example = "我想买一台5000元以内的游戏本")
    private String textContent;

    @Schema(description = "文件OSS地址（inputType=image/voice时使用）",
            example = "https://oss.ilbuy.com/input/image/xxx.jpg")
    private String fileUrl;

    @Schema(description = "商品链接（inputType=link时必填）",
            example = "https://item.jd.com/100012345.html")
    private String rawUrl;

    @Schema(description = "语音识别提供方，可选 baidu/ifly，默认baidu", example = "baidu")
    private String voiceProvider;

    @Schema(description = "用户ID（JWT中自动提取，前端可忽略）")
    private Long userId;

    @Schema(description = "请求唯一追踪ID（选填，便于日志排查）")
    private String traceId;
}
