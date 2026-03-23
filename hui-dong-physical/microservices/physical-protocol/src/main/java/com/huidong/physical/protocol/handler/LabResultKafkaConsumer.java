package com.huidong.physical.protocol.handler;

import com.alibaba.fastjson2.JSON;
import com.huidong.physical.protocol.dto.HL7ParseResult;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

/**
 * 检验结果 Kafka 消费者（自消费，供二次处理或日志审计使用）
 * 实际业务消费在 physical-core 中完成
 */
@Slf4j
@Component
public class LabResultKafkaConsumer {

    @KafkaListener(topics = "physical.lab.result.audit", groupId = "protocol-audit-group")
    public void onAuditMessage(ConsumerRecord<String, String> record) {
        try {
            HL7ParseResult result = JSON.parseObject(record.value(), HL7ParseResult.class);
            log.info("[审计] 检验结果处理: patientId={}, items={}",
                    result.getPatientId(),
                    result.getItems() != null ? result.getItems().size() : 0);
        } catch (Exception e) {
            log.error("[审计] 消费失败: key={}, error={}", record.key(), e.getMessage());
        }
    }
}
