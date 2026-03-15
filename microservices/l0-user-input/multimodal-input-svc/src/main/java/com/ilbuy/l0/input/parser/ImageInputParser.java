package com.ilbuy.l0.input.parser;

import com.ilbuy.l0.input.domain.dto.InputRequest;
import com.ilbuy.l0.input.domain.dto.ParsedInput;
import com.ilbuy.l0.input.domain.enums.InputType;
import com.ilbuy.l0.input.service.ImageRecognitionService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * 图片输入解析器
 *
 * <p>调用图像识别服务（{@link ImageRecognitionService}）对图片进行商品分类识别，
 * 提取商品标签，转换为标准化 {@link ParsedInput}。
 *
 * <p>图像识别采用轻量级封装：
 * <ul>
 *   <li>Dev环境：Mock识别（返回配置化的示例标签）</li>
 *   <li>Prod环境：调用内部L3 Python图像识别微服务（cv-recognition-svc）</li>
 * </ul>
 *
 * @author ILbuy Team
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ImageInputParser implements InputParser {

    private final ImageRecognitionService imageRecognitionService;

    @Override
    public InputType supportedType() {
        return InputType.IMAGE;
    }

    @Override
    public ParsedInput parse(InputRequest request) {
        String imageUrl = request.getFileUrl();
        if (StringUtils.isBlank(imageUrl)) {
            return ParsedInput.builder()
                    .userId(request.getUserId())
                    .inputType(InputType.IMAGE)
                    .success(false)
                    .failReason("图片URL不能为空")
                    .build();
        }

        log.debug("[ImageParser] 开始识别图片: {}", imageUrl);

        try {
            ImageRecognitionService.RecognitionResult recognition =
                    imageRecognitionService.recognize(imageUrl);

            if (!recognition.isSuccess()) {
                return ParsedInput.builder()
                        .userId(request.getUserId())
                        .inputType(InputType.IMAGE)
                        .imageUrl(imageUrl)
                        .success(false)
                        .failReason("图像识别失败: " + recognition.getFailReason())
                        .build();
            }

            List<String> labels = recognition.getLabels();
            // 置信度最高的标签作为关键词
            String primaryKeyword = labels.isEmpty() ? "未知商品" : labels.get(0);

            log.info("[ImageParser] 图像识别完成: labels={}, primaryKeyword={}",
                    labels, primaryKeyword);

            return ParsedInput.builder()
                    .userId(request.getUserId())
                    .inputType(InputType.IMAGE)
                    .rawInput(imageUrl)
                    .imageUrl(imageUrl)
                    .detectedLabels(labels)
                    .productKeyword(primaryKeyword)
                    .requirement("图片识别：" + String.join("、", labels))
                    .success(true)
                    .build();

        } catch (Exception e) {
            log.error("[ImageParser] 图像识别异常: url={}", imageUrl, e);
            return ParsedInput.builder()
                    .userId(request.getUserId())
                    .inputType(InputType.IMAGE)
                    .imageUrl(imageUrl)
                    .success(false)
                    .failReason("图像识别服务异常: " + e.getMessage())
                    .build();
        }
    }
}
