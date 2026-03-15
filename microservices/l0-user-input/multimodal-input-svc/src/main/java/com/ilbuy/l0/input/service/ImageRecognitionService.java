package com.ilbuy.l0.input.service;

import lombok.Builder;
import lombok.Data;

import java.util.List;

/**
 * 图像识别服务接口（商品识别）
 *
 * <p>封装两种实现：
 * <ul>
 *   <li>Dev：{@link com.ilbuy.l0.input.service.impl.InternalImageRecognitionService}
 *       在dev环境返回Mock数据，不依赖外部服务</li>
 *   <li>Prod：调用内部 L3 cv-recognition-svc Python微服务（OpenCV + ResNet）</li>
 * </ul>
 *
 * @author ILbuy Team
 */
public interface ImageRecognitionService {

    /**
     * 识别图片中的商品类别
     *
     * @param imageUrl 图片OSS地址或公网URL
     * @return 识别结果（包含标签列表，按置信度降序）
     */
    RecognitionResult recognize(String imageUrl);

    @Data
    @Builder
    class RecognitionResult {
        /** 按置信度降序排列的标签列表 */
        private List<String> labels;
        /** 各标签对应的置信度（0-1） */
        private List<Double> confidences;
        private boolean      success;
        private String       failReason;

        public static RecognitionResult ok(List<String> labels, List<Double> confidences) {
            return RecognitionResult.builder()
                    .labels(labels).confidences(confidences).success(true).build();
        }

        public static RecognitionResult fail(String reason) {
            return RecognitionResult.builder()
                    .success(false).failReason(reason).build();
        }
    }
}
