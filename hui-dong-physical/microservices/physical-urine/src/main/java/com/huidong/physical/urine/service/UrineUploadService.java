package com.huidong.physical.urine.service;

import com.alibaba.fastjson2.JSON;
import com.huidong.physical.urine.dto.UrineUploadDTO;
import com.huidong.physical.urine.dto.UrineUploadResultVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * 下乡尿机数据上传服务
 * 核心能力：幂等去重 + Kafka异步推送到core服务
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class UrineUploadService {

    private static final String UPLOAD_ID_KEY = "physical:urine:uploadId:";
    private static final String TOPIC_URINE_RESULT = "physical.urine.result";
    private static final long DEDUP_EXPIRE_HOURS = 48;

    private final StringRedisTemplate redisTemplate;
    private final KafkaTemplate<String, String> kafkaTemplate;

    /**
     * 上传尿常规数据
     * 使用uploadId实现幂等，防止4G/5G弱网重试导致重复入库
     */
    public UrineUploadResultVO upload(UrineUploadDTO dto) {
        String dedupKey = UPLOAD_ID_KEY + dto.getUploadId();

        // 幂等检查：同一uploadId已处理过，直接返回
        Boolean isNew = redisTemplate.opsForValue().setIfAbsent(
                dedupKey, "processed", DEDUP_EXPIRE_HOURS, TimeUnit.HOURS);

        UrineUploadResultVO vo = new UrineUploadResultVO();
        vo.setUploadId(dto.getUploadId());

        if (Boolean.FALSE.equals(isNew)) {
            log.info("[尿机] 重复上传，已忽略: uploadId={}", dto.getUploadId());
            vo.setStatus("DUPLICATE");
            vo.setMessage("重复上传，数据已处理");
            return vo;
        }

        // 推送到Kafka，由core服务异步入库
        String message = JSON.toJSONString(dto);
        kafkaTemplate.send(TOPIC_URINE_RESULT, dto.getResidentIdentifier(), message)
                .addCallback(
                        success -> log.info("[尿机] 上传成功: uploadId={}, residentId={}",
                                dto.getUploadId(), dto.getResidentIdentifier()),
                        failure -> {
                            // Kafka推送失败时清除去重key，允许重试
                            redisTemplate.delete(dedupKey);
                            log.error("[尿机] Kafka推送失败: uploadId={}, error={}",
                                    dto.getUploadId(), failure.getMessage());
                        }
                );

        vo.setStatus("ACCEPTED");
        vo.setMessage("数据已接收，正在处理");
        return vo;
    }

    /**
     * 查询上传状态
     */
    public String queryUploadStatus(String uploadId) {
        String key = UPLOAD_ID_KEY + uploadId;
        String value = redisTemplate.opsForValue().get(key);
        return value != null ? "PROCESSED" : "NOT_FOUND";
    }

    /**
     * 批量上传（弱网恢复场景：手提电脑重新联网后批量补传）
     */
    public void batchUpload(List<UrineUploadDTO> list) {
        log.info("[尿机] 批量上传: count={}", list.size());
        list.forEach(dto -> {
            try {
                upload(dto);
            } catch (Exception e) {
                log.error("[尿机] 批量上传单条失败: uploadId={}, error={}", dto.getUploadId(), e.getMessage());
            }
        });
    }
}
