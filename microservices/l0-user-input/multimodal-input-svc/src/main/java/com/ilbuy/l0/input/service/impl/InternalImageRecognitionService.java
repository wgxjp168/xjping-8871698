package com.ilbuy.l0.input.service.impl;

import cn.hutool.http.HttpRequest;
import cn.hutool.http.HttpResponse;
import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import com.ilbuy.l0.input.service.ImageRecognitionService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

/**
 * 图像识别服务实现
 *
 * <p>路由策略：
 * <ul>
 *   <li>Dev（{@code ilbuy.image.mock-enabled=true}）：返回固定Mock标签，无需外部依赖</li>
 *   <li>Prod（{@code ilbuy.image.mock-enabled=false}）：调用内部 cv-recognition-svc
 *       Python微服务（L3层，OpenCV + ResNet-50商品分类模型），端口 9300</li>
 * </ul>
 *
 * <p>内部服务接口（cv-recognition-svc）：
 * <pre>
 * POST http://cv-recognition-svc:9300/api/v1/recognize
 * Body: { "imageUrl": "https://..." }
 * Response: { "labels": ["笔记本电脑", "游戏本"], "confidences": [0.95, 0.87] }
 * </pre>
 *
 * @author ILbuy Team
 */
@Slf4j
@Service
public class InternalImageRecognitionService implements ImageRecognitionService {

    @Value("${ilbuy.image.mock-enabled:true}")
    private boolean mockEnabled;

    @Value("${ilbuy.image.cv-service-url:http://cv-recognition-svc:9300}")
    private String cvServiceUrl;

    private static final int TIMEOUT_MS = 8_000;

    @Override
    public RecognitionResult recognize(String imageUrl) {
        if (mockEnabled) {
            return mockRecognize(imageUrl);
        }
        return callCvService(imageUrl);
    }

    private RecognitionResult mockRecognize(String imageUrl) {
        log.debug("[ImageRecognition] Mock模式：返回示例标签, url={}", imageUrl);
        // Mock：根据URL关键词返回不同标签（仅用于dev测试）
        List<String> labels;
        List<Double> confidences;
        String lower = imageUrl.toLowerCase();
        if (lower.contains("laptop") || lower.contains("notebook") || lower.contains("电脑")) {
            labels = List.of("笔记本电脑", "游戏本", "电子设备");
            confidences = List.of(0.95, 0.87, 0.76);
        } else if (lower.contains("phone") || lower.contains("手机")) {
            labels = List.of("智能手机", "手机", "电子产品");
            confidences = List.of(0.93, 0.85, 0.70);
        } else if (lower.contains("shoe") || lower.contains("鞋")) {
            labels = List.of("运动鞋", "鞋子", "服饰鞋包");
            confidences = List.of(0.91, 0.88, 0.72);
        } else {
            labels = List.of("商品", "消费品");
            confidences = List.of(0.60, 0.50);
        }
        return RecognitionResult.ok(labels, confidences);
    }

    private RecognitionResult callCvService(String imageUrl) {
        try {
            String endpoint = cvServiceUrl + "/api/v1/recognize";
            JSONObject body = JSONUtil.createObj().set("imageUrl", imageUrl);

            HttpResponse response = HttpRequest.post(endpoint)
                    .header("Content-Type", "application/json")
                    .body(body.toString())
                    .timeout(TIMEOUT_MS)
                    .execute();

            if (!response.isOk()) {
                return RecognitionResult.fail("cv-recognition-svc 返回异常: HTTP " + response.getStatus());
            }

            JSONObject result = JSONUtil.parseObj(response.body());
            JSONArray labelsArr = result.getJSONArray("labels");
            JSONArray confArr   = result.getJSONArray("confidences");

            List<String> labels = new ArrayList<>();
            List<Double> confidences = new ArrayList<>();

            if (labelsArr != null) {
                labelsArr.forEach(l -> labels.add(l.toString()));
            }
            if (confArr != null) {
                confArr.forEach(c -> confidences.add(Double.parseDouble(c.toString())));
            }

            log.info("[ImageRecognition] cv-recognition-svc 识别完成: labels={}", labels);
            return RecognitionResult.ok(labels, confidences);

        } catch (Exception e) {
            log.error("[ImageRecognition] 调用cv-recognition-svc失败: url={}", imageUrl, e);
            return RecognitionResult.fail("图像识别服务调用失败: " + e.getMessage());
        }
    }
}
