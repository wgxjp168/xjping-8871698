package com.huidong.physical.sync.config;

import com.alibaba.fastjson2.JSON;
import com.huidong.physical.sync.service.SyncService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * 同步服务 Kafka 消费者
 * 监听core服务产生的体检完成事件，触发上报县域公卫平台
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class SyncKafkaConsumer {

    private final SyncService syncService;

    /**
     * 监听体检单完成事件
     */
    @KafkaListener(topics = "physical.exam.completed", groupId = "sync-group")
    public void onExamCompleted(ConsumerRecord<String, String> record) {
        try {
            Map<String, Object> examData = JSON.parseObject(record.value(), Map.class);
            Long examRecordId = Long.valueOf(examData.getOrDefault("examRecordId", "0").toString());
            syncService.syncExamData(examRecordId, examData);
            log.info("[同步] 体检单上报触发: examRecordId={}", examRecordId);
        } catch (Exception e) {
            log.error("[同步] 体检单消费失败: key={}, error={}", record.key(), e.getMessage());
        }
    }

    /**
     * 监听检验结果完成事件
     */
    @KafkaListener(topics = "physical.lab.completed", groupId = "sync-group")
    public void onLabCompleted(ConsumerRecord<String, String> record) {
        try {
            Map<String, Object> labData = JSON.parseObject(record.value(), Map.class);
            Long labResultId = Long.valueOf(labData.getOrDefault("labResultId", "0").toString());
            syncService.syncLabResult(labResultId, labData);
            log.info("[同步] 检验结果上报触发: labResultId={}", labResultId);
        } catch (Exception e) {
            log.error("[同步] 检验结果消费失败: key={}, error={}", record.key(), e.getMessage());
        }
    }
}
