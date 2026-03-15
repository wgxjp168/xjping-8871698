package com.ilbuy.l0.input.domain.dto;

import com.ilbuy.l0.input.domain.enums.InputType;
import com.ilbuy.l0.input.parser.platform.EcommercePlatform;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * 多模态输入解析结果
 *
 * <p>所有输入类型（文本/图片/链接/语音）最终统一转换为此对象，
 * 向下游 L1 网关及 L2 AI 决策层传递标准化信号。
 *
 * <p>字段说明：
 * <ul>
 *   <li>productKeyword - 核心商品关键词（最重要的标准化结果）</li>
 *   <li>requirement    - 用户需求文本（原始语义）</li>
 *   <li>budgetMin/Max  - 识别出的预算区间（元），可为null</li>
 *   <li>platform       - 来源电商平台（LINK输入有效）</li>
 *   <li>platformProductId - 平台商品ID（LINK输入有效）</li>
 *   <li>normalizedUrl  - 标准化后的商品URL（去掉追踪参数）</li>
 *   <li>imageUrl       - 图片URL（IMAGE输入有效）</li>
 *   <li>detectedLabels - 图像识别标签列表（IMAGE输入有效）</li>
 *   <li>transcribedText - 语音转换后的文本（VOICE输入有效）</li>
 *   <li>metadata       - 额外扩展信息</li>
 * </ul>
 *
 * @author ILbuy Team
 */
@Data
@Builder
@Schema(description = "多模态输入解析结果")
public class ParsedInput {

    @Schema(description = "用户ID")
    private Long userId;

    @Schema(description = "原始输入类型")
    private InputType inputType;

    @Schema(description = "核心商品关键词", example = "游戏本")
    private String productKeyword;

    @Schema(description = "用户需求文本（标准化）", example = "我想买一台5000元以内的游戏本")
    private String requirement;

    @Schema(description = "最低预算（元）", example = "3000")
    private BigDecimal budgetMin;

    @Schema(description = "最高预算（元）", example = "5000")
    private BigDecimal budgetMax;

    @Schema(description = "来源电商平台（链接输入有效）")
    private EcommercePlatform platform;

    @Schema(description = "平台商品ID（链接输入有效）", example = "100012345")
    private String platformProductId;

    @Schema(description = "标准化商品URL（去除追踪参数）",
            example = "https://item.jd.com/100012345.html")
    private String normalizedUrl;

    @Schema(description = "图片URL（图片输入有效）")
    private String imageUrl;

    @Schema(description = "图像识别标签（图片输入有效）", example = "[\"笔记本电脑\", \"游戏本\"]")
    private List<String> detectedLabels;

    @Schema(description = "语音转文本结果（语音输入有效）", example = "我想买游戏本")
    private String transcribedText;

    @Schema(description = "原始输入内容（用于日志审计）")
    private String rawInput;

    @Schema(description = "扩展信息")
    private Map<String, Object> metadata;

    @Schema(description = "解析是否成功")
    private boolean success;

    @Schema(description = "失败原因（success=false时有效）")
    private String failReason;
}
