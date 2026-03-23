package com.huidong.physical.sync.service;

import com.alibaba.fastjson2.JSON;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

/**
 * 惠东县县域智慧公卫系统 - HTTP客户端
 * 负责调用上级平台开放接口
 */
@Slf4j
@Service
public class CountyPlatformClient {

    @Value("${county.platform.base-url:http://127.0.0.1:8080}")
    private String baseUrl;

    @Value("${county.platform.app-key:}")
    private String appKey;

    @Value("${county.platform.app-secret:}")
    private String appSecret;

    private final RestTemplate restTemplate;

    public CountyPlatformClient() {
        this.restTemplate = new RestTemplate();
    }

    /**
     * 上报体检数据到县域公卫系统
     *
     * @param examData 体检数据（JSON格式，按县域平台接口规范）
     * @return 上报结果 true=成功
     */
    public boolean reportExamData(Map<String, Object> examData) {
        String url = baseUrl + "/api/physical/exam/report";
        return doPost(url, examData);
    }

    /**
     * 上报检验结果到县域公卫系统
     */
    public boolean reportLabResult(Map<String, Object> labData) {
        String url = baseUrl + "/api/physical/lab/report";
        return doPost(url, labData);
    }

    private boolean doPost(String url, Object body) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("X-App-Key", appKey);
            headers.set("X-Timestamp", String.valueOf(System.currentTimeMillis()));
            // TODO: 实际签名算法按县域平台文档实现
            headers.set("X-Sign", buildSign(body));

            HttpEntity<String> request = new HttpEntity<>(JSON.toJSONString(body), headers);
            ResponseEntity<String> response = restTemplate.postForEntity(url, request, String.class);

            if (response.getStatusCode() == HttpStatus.OK) {
                Map<?, ?> result = JSON.parseObject(response.getBody(), Map.class);
                Object code = result.get("code");
                boolean success = "200".equals(String.valueOf(code)) || Integer.valueOf(200).equals(code);
                log.info("上报县域平台: url={}, success={}", url, success);
                return success;
            }
            log.warn("上报县域平台失败: url={}, httpStatus={}", url, response.getStatusCode());
            return false;

        } catch (Exception e) {
            log.error("上报县域平台异常: url={}, error={}", url, e.getMessage());
            return false;
        }
    }

    private String buildSign(Object body) {
        // TODO: 按照县域公卫平台接口鉴权文档实现签名
        return cn.hutool.crypto.SecureUtil.md5(appKey + JSON.toJSONString(body) + appSecret);
    }
}
