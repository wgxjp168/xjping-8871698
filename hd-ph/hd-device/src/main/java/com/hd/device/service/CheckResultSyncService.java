package com.hd.device.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.hd.device.entity.DeviceCheckOrder;
import com.hd.device.entity.DeviceCheckResult;
import com.hd.device.entity.DeviceInfo;
import com.hd.device.entity.DeviceRawData;
import com.hd.device.mapper.DeviceCheckOrderMapper;
import com.hd.device.mapper.DeviceCheckResultMapper;
import com.hd.device.mapper.DeviceInfoMapper;
import com.hd.device.mapper.DeviceRawDataMapper;
import com.hd.device.protocol.DeviceItemCodeMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * 检验结果同步服务
 * 定时从 device_raw_data 读取待处理记录，解析后写入 check_result 表
 *
 * 流程：
 *   1. 查询 device_raw_data WHERE process_status=0
 *   2. 解析 parsed_json (sampleId + 检验结果列表)
 *   3. 通过 sampleId = order_no 匹配 check_order
 *   4. 将每个检验项目写入 check_result（含公卫标准编码）
 *   5. 标记 device_raw_data.process_status=1（成功）或2（失败）
 */
@Service
public class CheckResultSyncService {

    private static final Logger log = LoggerFactory.getLogger(CheckResultSyncService.class);

    @Autowired
    private DeviceRawDataMapper rawDataMapper;

    @Autowired
    private DeviceCheckOrderMapper checkOrderMapper;

    @Autowired
    private DeviceCheckResultMapper checkResultMapper;

    @Autowired
    private DeviceInfoMapper deviceInfoMapper;

    @Autowired
    private DeviceItemCodeMapper itemCodeMapper;

    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * 每30秒执行一次同步
     */
    @Scheduled(fixedDelay = 30000)
    public void syncPendingResults() {
        List<DeviceRawData> pendingList = rawDataMapper.selectList(
                new LambdaQueryWrapper<DeviceRawData>()
                        .eq(DeviceRawData::getProcessStatus, 0)
                        .eq(DeviceRawData::getDeleted, 0)
                        .orderByAsc(DeviceRawData::getCreateTime)
                        .last("LIMIT 50")
        );
        if (pendingList.isEmpty()) return;

        log.info("Syncing {} pending device results to check_result", pendingList.size());
        for (DeviceRawData rawData : pendingList) {
            try {
                processSingleRecord(rawData);
            } catch (Exception e) {
                log.error("Failed to process raw data id={}: {}", rawData.getId(), e.getMessage(), e);
                markFailed(rawData.getId(), e.getMessage());
            }
        }
    }

    @Transactional
    public void processSingleRecord(DeviceRawData rawData) throws Exception {
        String json = rawData.getParsedJson();
        if (json == null || json.equals("{}")) {
            markFailed(rawData.getId(), "parsed_json is empty");
            return;
        }

        Map<String, Object> parsed = objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {});
        String sampleId = (String) parsed.get("sampleId");
        if (sampleId == null || sampleId.isEmpty()) {
            sampleId = rawData.getSampleId();
        }

        // 通过 sampleId 匹配 check_order（sampleId = order_no = 体检条码）
        DeviceCheckOrder order = findOrder(sampleId, rawData.getPatientId());
        if (order == null) {
            log.warn("No check_order found for sampleId={}, patientId={}, raw_data_id={}",
                    sampleId, rawData.getPatientId(), rawData.getId());
            markFailed(rawData.getId(), "No matching check_order for sampleId=" + sampleId);
            return;
        }

        // 获取设备信息
        DeviceInfo device = rawData.getDeviceId() != null
                ? deviceInfoMapper.selectById(rawData.getDeviceId()) : null;
        String deviceCategory = device != null ? device.getDeviceType() : null;

        // 解析检验结果列表
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> results = (List<Map<String, Object>>) parsed.get("results");
        if (results == null || results.isEmpty()) {
            markFailed(rawData.getId(), "No results in parsed_json");
            return;
        }

        int written = 0;
        for (Map<String, Object> item : results) {
            String testCode = (String) item.get("testCode");
            String testName = (String) item.get("testName");
            String value = (String) item.get("value");
            String unit = (String) item.get("unit");
            String refRange = (String) item.get("referenceRange");
            String flag = (String) item.get("flag");

            // 映射到公卫标准编码
            DeviceItemCodeMapper.ItemMapping mapping = itemCodeMapper.getMapping(testCode);
            String stdCode = mapping != null ? mapping.standardCode : testCode;
            String stdName = mapping != null ? mapping.standardName : testName;
            String category = mapping != null ? mapping.category
                    : itemCodeMapper.inferCategory(deviceCategory);

            // 标准化flag
            String normalizedFlag = normalizeFlag(flag);

            DeviceCheckResult result = new DeviceCheckResult();
            result.setOrderId(order.getId());
            result.setOrderNo(order.getOrderNo());
            result.setResidentId(order.getResidentId());
            result.setCategory(category);
            result.setItemCode(stdCode);
            result.setItemName(stdName);
            result.setValueStr(value);
            result.setValueNum(parseDecimal(value));
            result.setUnit(unit);
            result.setRefRange(refRange);
            result.setFlag(normalizedFlag);
            result.setDeviceId(rawData.getDeviceId());
            result.setDeviceCode(device != null ? device.getDeviceNo() : null);
            result.setDeviceModel(device != null ? device.getDeviceModel() : null);
            result.setDataSource("DEVICE");
            result.setSampleId(sampleId);
            result.setCheckTime(rawData.getCreateTime());
            result.setUploadStatus(0);
            result.setCreateTime(LocalDateTime.now());
            result.setUpdateTime(LocalDateTime.now());
            result.setDeleted(0);

            checkResultMapper.insert(result);
            written++;
        }

        // 标记为已处理
        DeviceRawData update = new DeviceRawData();
        update.setId(rawData.getId());
        update.setProcessStatus(1);
        update.setUpdateTime(LocalDateTime.now());
        rawDataMapper.updateById(update);

        log.info("Synced raw_data id={}, sampleId={}, order_no={}, wrote {} result(s)",
                rawData.getId(), sampleId, order.getOrderNo(), written);
    }

    private DeviceCheckOrder findOrder(String sampleId, String patientId) {
        if (sampleId != null && !sampleId.isEmpty()) {
            DeviceCheckOrder o = checkOrderMapper.selectOne(
                    new LambdaQueryWrapper<DeviceCheckOrder>()
                            .eq(DeviceCheckOrder::getOrderNo, sampleId)
            );
            if (o != null) return o;
        }
        if (patientId != null && !patientId.isEmpty()) {
            // patientId 可能是 id_card 或 resident_id
            DeviceCheckOrder o = checkOrderMapper.selectOne(
                    new LambdaQueryWrapper<DeviceCheckOrder>()
                            .eq(DeviceCheckOrder::getIdCard, patientId)
            );
            if (o != null) return o;
        }
        return null;
    }

    private void markFailed(Long id, String msg) {
        DeviceRawData raw = new DeviceRawData();
        raw.setId(id);
        raw.setProcessStatus(2);
        raw.setErrorMsg(msg != null && msg.length() > 500 ? msg.substring(0, 500) : msg);
        raw.setUpdateTime(LocalDateTime.now());
        rawDataMapper.updateById(raw);
    }

    /**
     * 将字符串解析为 BigDecimal，失败返回 null
     */
    private BigDecimal parseDecimal(String value) {
        if (value == null || value.trim().isEmpty()) return null;
        try {
            // 去掉非数字字符后尝试解析（如 ">60" → 60）
            String clean = value.trim().replaceAll("[^0-9.\\-]", "");
            if (clean.isEmpty()) return null;
            return new BigDecimal(clean);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    /**
     * 标准化异常标志：H/L/A/N
     */
    private String normalizeFlag(String flag) {
        if (flag == null || flag.isEmpty()) return "N";
        String f = flag.toUpperCase().trim();
        if (f.contains("H") || f.contains("↑")) return "H";
        if (f.contains("L") || f.contains("↓")) return "L";
        if (f.contains("A")) return "A";
        return "N";
    }
}
