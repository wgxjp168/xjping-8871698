package com.hd.device.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.hd.device.entity.DeviceInfo;
import com.hd.device.entity.DeviceRawData;
import com.hd.device.mapper.DeviceInfoMapper;
import com.hd.device.mapper.DeviceRawDataMapper;
import com.hd.device.protocol.AstmMessage;
import com.hd.device.protocol.AstmParser;
import com.hd.device.protocol.AstmRecord;
import com.hd.device.protocol.ParsedResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class DeviceDataService {

    private static final Logger log = LoggerFactory.getLogger(DeviceDataService.class);

    @Autowired
    private DeviceInfoMapper deviceInfoMapper;

    @Autowired
    private DeviceRawDataMapper rawDataMapper;

    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * 保存 ASTM 消息到 device_raw_data 表
     */
    public void saveAstmMessage(AstmMessage message, String rawText, String remoteAddr) {
        // 查找设备（按IP匹配）
        Long deviceId = findDeviceIdByAddr(remoteAddr);

        // 解析所有 R 记录
        List<Map<String, Object>> results = new ArrayList<>();
        for (AstmRecord rRecord : message.getResultRecords()) {
            ParsedResult pr = AstmParser.parseResultRecord(rRecord);
            Map<String, Object> item = new HashMap<>();
            item.put("testCode", pr.getTestCode());
            item.put("testName", pr.getTestName());
            item.put("value", pr.getValue());
            item.put("unit", pr.getUnit());
            item.put("referenceRange", pr.getReferenceRange());
            item.put("flag", pr.getFlag());
            item.put("abnormal", pr.isAbnormal());
            results.add(item);
        }

        String parsedJson = "{}";
        try {
            Map<String, Object> jsonData = new HashMap<>();
            jsonData.put("sampleId", message.getSampleId());
            jsonData.put("patientId", message.getPatientId());
            jsonData.put("results", results);
            parsedJson = objectMapper.writeValueAsString(jsonData);
        } catch (Exception e) {
            log.error("JSON serialization error", e);
        }

        DeviceRawData rawData = new DeviceRawData();
        rawData.setDeviceId(deviceId);
        rawData.setPatientId(message.getPatientId());
        rawData.setSampleId(message.getSampleId());
        rawData.setRawMessage(rawText);
        rawData.setParsedJson(parsedJson);
        rawData.setProcessStatus(0); // 待处理
        rawData.setCreateTime(LocalDateTime.now());
        rawData.setUpdateTime(LocalDateTime.now());
        rawData.setDeleted(0);
        rawDataMapper.insert(rawData);

        log.info("Saved raw data, id={}, sampleId={}", rawData.getId(), message.getSampleId());
    }

    private Long findDeviceIdByAddr(String remoteAddr) {
        if (remoteAddr == null) return null;
        // 提取 IP 地址
        String ip = remoteAddr.replaceAll(".*/(\\d+\\.\\d+\\.\\d+\\.\\d+).*", "$1");
        DeviceInfo device = deviceInfoMapper.selectOne(
                new LambdaQueryWrapper<DeviceInfo>()
                        .eq(DeviceInfo::getIpAddress, ip)
                        .eq(DeviceInfo::getDeleted, 0)
        );
        return device != null ? device.getId() : null;
    }

    public List<DeviceRawData> listPendingData() {
        return rawDataMapper.selectList(
                new LambdaQueryWrapper<DeviceRawData>()
                        .eq(DeviceRawData::getProcessStatus, 0)
                        .eq(DeviceRawData::getDeleted, 0)
                        .orderByAsc(DeviceRawData::getCreateTime)
        );
    }

    public void markProcessed(Long id) {
        DeviceRawData raw = new DeviceRawData();
        raw.setId(id);
        raw.setProcessStatus(1);
        raw.setUpdateTime(LocalDateTime.now());
        rawDataMapper.updateById(raw);
    }

    public void markFailed(Long id, String errorMsg) {
        DeviceRawData raw = new DeviceRawData();
        raw.setId(id);
        raw.setProcessStatus(2);
        raw.setErrorMsg(errorMsg);
        raw.setUpdateTime(LocalDateTime.now());
        rawDataMapper.updateById(raw);
    }
}
