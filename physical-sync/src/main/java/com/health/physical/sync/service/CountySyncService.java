package com.health.physical.sync.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.health.physical.common.entity.PhysicalRecord;
import com.health.physical.sync.mapper.PhysicalSyncMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 县域公卫同步服务
 * 将区域系统体检数据同步至惠东县县域公卫系统
 */
@Slf4j
@Service
@EnableScheduling
@RequiredArgsConstructor
public class CountySyncService {

    private final PhysicalSyncMapper physicalSyncMapper;
    private final RestTemplate restTemplate;

    @Value("${county.api.base-url:http://county-gateway:8080}")
    private String countyApiBaseUrl;

    @Value("${county.api.token:}")
    private String countyApiToken;

    /**
     * 每10分钟批量同步体检数据至县域
     */
    @Scheduled(fixedDelay = 10 * 60 * 1000)
    public void batchSyncPhysicalToCounty() {
        log.debug("[同步服务] 开始批量同步体检数据至县域...");
        List<PhysicalRecord> pendingList = physicalSyncMapper.selectPendingSync(100);
        if (pendingList.isEmpty()) {
            return;
        }
        log.info("[同步服务] 待同步体检记录: {}条", pendingList.size());
        int success = 0, fail = 0;
        for (PhysicalRecord record : pendingList) {
            try {
                syncPhysicalRecord(record);
                // 更新同步状态为已同步
                physicalSyncMapper.update(null, new LambdaUpdateWrapper<PhysicalRecord>()
                        .eq(PhysicalRecord::getId, record.getId())
                        .set(PhysicalRecord::getSyncStatus, 1));
                success++;
            } catch (Exception e) {
                log.error("[同步服务] 体检记录同步失败: id={}, error={}", record.getId(), e.getMessage());
                // 标记为同步失败
                physicalSyncMapper.update(null, new LambdaUpdateWrapper<PhysicalRecord>()
                        .eq(PhysicalRecord::getId, record.getId())
                        .set(PhysicalRecord::getSyncStatus, 2));
                fail++;
            }
        }
        log.info("[同步服务] 本次同步完成: 成功={}, 失败={}", success, fail);
    }

    /**
     * 同步单条体检记录至县域
     */
    public void syncPhysicalRecord(PhysicalRecord record) {
        String url = countyApiBaseUrl + "/api/physical/upload";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        if (countyApiToken != null && !countyApiToken.isBlank()) {
            headers.set("Authorization", "Bearer " + countyApiToken);
        }

        Map<String, Object> body = buildSyncBody(record);
        HttpEntity<String> entity = new HttpEntity<>(JSON.toJSONString(body), headers);

        ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.POST, entity, String.class);
        if (response.getStatusCode().is2xxSuccessful()) {
            JSONObject result = JSON.parseObject(response.getBody());
            String countyId = result.getString("data");
            if (countyId != null) {
                physicalSyncMapper.update(null, new LambdaUpdateWrapper<PhysicalRecord>()
                        .eq(PhysicalRecord::getId, record.getId())
                        .set(PhysicalRecord::getCountyPhysicalId, countyId));
            }
            log.info("[同步服务] 体检记录同步成功: id={}, countyId={}", record.getId(), countyId);
        } else {
            throw new RuntimeException("县域接口返回非2xx: " + response.getStatusCode());
        }
    }

    private Map<String, Object> buildSyncBody(PhysicalRecord record) {
        Map<String, Object> body = new HashMap<>();
        body.put("residentId", record.getResidentId());
        body.put("examDate", record.getExamDate() != null ? record.getExamDate().toString() : null);
        body.put("batchNo", record.getBatchNo());
        body.put("orgName", record.getOrgName());
        body.put("weight", record.getWeight());
        body.put("height", record.getHeight());
        body.put("bmi", record.getBmi());
        body.put("systolicBp", record.getSystolicBp());
        body.put("diastolicBp", record.getDiastolicBp());
        body.put("operator", record.getOperator());
        return body;
    }
}
