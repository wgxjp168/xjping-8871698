package com.huidong.physical.protocol.service;

import com.alibaba.fastjson2.JSON;
import com.huidong.physical.protocol.dto.HL7ParseResult;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

/**
 * 检验结果分发器
 * 将解析后的结果通过Kafka推送到core服务
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class LabResultDispatcher {

    private static final String TOPIC_LAB_RESULT = "physical.lab.result";

    private final KafkaTemplate<String, String> kafkaTemplate;

    /**
     * 分发检验结果到核心业务服务
     */
    public void dispatch(HL7ParseResult result) {
        String message = JSON.toJSONString(result);
        kafkaTemplate.send(TOPIC_LAB_RESULT, result.getPatientId(), message)
                .addCallback(
                        success -> log.debug("检验结果推送成功: patientId={}", result.getPatientId()),
                        failure -> log.error("检验结果推送失败: patientId={}, error={}", result.getPatientId(), failure.getMessage())
                );
    }
}
