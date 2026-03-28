package com.hd.device.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.hd.device.entity.DeviceCheckOrder;
import com.hd.device.entity.DeviceCheckResult;
import com.hd.device.entity.DeviceInfo;
import com.hd.device.mapper.DeviceCheckOrderMapper;
import com.hd.device.mapper.DeviceCheckResultMapper;
import com.hd.device.mapper.DeviceInfoMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 公卫系统上传服务
 * 将检验结果上传至惠东县区域公卫体检集中系统（上级平台）
 *
 * 上传格式（JSON）：
 * {
 *   "hospitalCode": "HD_XXXX",
 *   "apiKey": "...",
 *   "patientInfo": { "examId": "...", "name": "...", "idCard": "..." },
 *   "deviceInfo": { "deviceCode": "...", "deviceType": "...", "deviceModel": "..." },
 *   "testResults": [ { "itemCode": "XCR001", "itemName": "白细胞", "value": "6.5", ... } ],
 *   "uploadTime": "2025-01-01 10:00:00"
 * }
 */
@Service
public class PublicHealthUploadService {

    private static final Logger log = LoggerFactory.getLogger(PublicHealthUploadService.class);
    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    @Value("${pubhealth.upload.enabled:false}")
    private boolean uploadEnabled;

    @Value("${pubhealth.upload.url:}")
    private String uploadUrl;

    @Value("${pubhealth.upload.api-key:}")
    private String apiKey;

    @Value("${pubhealth.upload.hospital-code:HD_DEFAULT}")
    private String hospitalCode;

    @Autowired
    private DeviceCheckResultMapper checkResultMapper;

    @Autowired
    private DeviceCheckOrderMapper checkOrderMapper;

    @Autowired
    private DeviceInfoMapper deviceInfoMapper;

    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * 每5分钟批量上传一次已完成但未上传的检验结果
     */
    @Scheduled(fixedDelay = 300000)
    public void uploadPendingResults() {
        if (!uploadEnabled || uploadUrl == null || uploadUrl.isEmpty()) {
            return;
        }

        List<DeviceCheckResult> pendingList = checkResultMapper.selectList(
                new LambdaQueryWrapper<DeviceCheckResult>()
                        .eq(DeviceCheckResult::getUploadStatus, 0)
                        .eq(DeviceCheckResult::getDeleted, 0)
                        .orderByAsc(DeviceCheckResult::getCreateTime)
                        .last("LIMIT 100")
        );
        if (pendingList.isEmpty()) return;

        log.info("Uploading {} results to public health system", pendingList.size());
        // 按 order_no 分组上传
        Map<String, List<DeviceCheckResult>> byOrder = new LinkedHashMap<>();
        for (DeviceCheckResult r : pendingList) {
            byOrder.computeIfAbsent(r.getOrderNo(), k -> new ArrayList<>()).add(r);
        }

        for (Map.Entry<String, List<DeviceCheckResult>> entry : byOrder.entrySet()) {
            uploadOrderResults(entry.getKey(), entry.getValue());
        }
    }

    /**
     * 手动触发单个体检单的结果上传
     */
    public boolean uploadByOrderNo(String orderNo) {
        List<DeviceCheckResult> results = checkResultMapper.selectList(
                new LambdaQueryWrapper<DeviceCheckResult>()
                        .eq(DeviceCheckResult::getOrderNo, orderNo)
                        .eq(DeviceCheckResult::getDeleted, 0)
        );
        if (results.isEmpty()) {
            log.warn("No results found for order {}", orderNo);
            return false;
        }
        return uploadOrderResults(orderNo, results);
    }

    private boolean uploadOrderResults(String orderNo, List<DeviceCheckResult> results) {
        if (results.isEmpty()) return true;

        // 查询体检单信息
        DeviceCheckOrder order = checkOrderMapper.selectOne(
                new LambdaQueryWrapper<DeviceCheckOrder>()
                        .eq(DeviceCheckOrder::getOrderNo, orderNo)
        );

        DeviceCheckResult first = results.get(0);
        DeviceInfo device = first.getDeviceId() != null
                ? deviceInfoMapper.selectById(first.getDeviceId()) : null;

        // 构造上传请求体
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("hospitalCode", hospitalCode);
        payload.put("apiKey", apiKey);

        Map<String, Object> patientInfo = new LinkedHashMap<>();
        patientInfo.put("examId", orderNo);
        if (order != null) {
            patientInfo.put("name", order.getResidentName());
            patientInfo.put("idCard", order.getIdCard());
        }
        payload.put("patientInfo", patientInfo);

        Map<String, Object> deviceInfo = new LinkedHashMap<>();
        deviceInfo.put("deviceCode", device != null ? device.getDeviceNo() : "UNKNOWN");
        deviceInfo.put("deviceType", device != null ? device.getDeviceType() : "");
        deviceInfo.put("deviceModel", device != null ? device.getDeviceModel() : "");
        payload.put("deviceInfo", deviceInfo);

        List<Map<String, Object>> testResults = new ArrayList<>();
        for (DeviceCheckResult r : results) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("itemCode", r.getItemCode());
            item.put("itemName", r.getItemName());
            item.put("value", r.getValueStr());
            item.put("valueNum", r.getValueNum());
            item.put("unit", r.getUnit());
            item.put("refRange", r.getRefRange());
            item.put("flag", r.getFlag());
            item.put("category", r.getCategory());
            testResults.add(item);
        }
        payload.put("testResults", testResults);
        payload.put("uploadTime", LocalDateTime.now().format(FORMATTER));

        try {
            String responseJson = restTemplate.postForObject(uploadUrl, payload, String.class);
            @SuppressWarnings("unchecked")
            Map<String, Object> response = objectMapper.readValue(responseJson, Map.class);
            Object code = response.get("code");
            boolean success = "200".equals(String.valueOf(code)) || Integer.valueOf(200).equals(code);

            if (success) {
                // 标记已上传
                for (DeviceCheckResult r : results) {
                    DeviceCheckResult upd = new DeviceCheckResult();
                    upd.setId(r.getId());
                    upd.setUploadStatus(1);
                    upd.setUpdateTime(LocalDateTime.now());
                    checkResultMapper.updateById(upd);
                }
                log.info("Upload success: order={}, items={}", orderNo, results.size());
                return true;
            } else {
                log.warn("Upload failed for order {}: {}", orderNo, response.get("msg"));
                return false;
            }
        } catch (Exception e) {
            log.error("Upload error for order {}: {}", orderNo, e.getMessage());
            return false;
        }
    }
}
