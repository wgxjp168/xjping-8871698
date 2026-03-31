package com.hd.device.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.hd.device.entity.DeviceRawData;
import com.hd.device.mapper.DeviceRawDataMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class CheckResultSyncService {

    private static final Logger log = LoggerFactory.getLogger(CheckResultSyncService.class);

    @Autowired
    private DeviceRawDataMapper deviceRawDataMapper;

    /**
     * Periodically sync pending device raw data results.
     * Runs every 30 seconds.
     */
    @Scheduled(fixedRate = 30000)
    public void syncPendingResults() {
        LambdaQueryWrapper<DeviceRawData> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(DeviceRawData::getProcessStatus, 0);
        wrapper.eq(DeviceRawData::getDeleted, 0);
        wrapper.orderByAsc(DeviceRawData::getCreateTime);
        wrapper.last("LIMIT 50");

        List<DeviceRawData> pendingList = deviceRawDataMapper.selectList(wrapper);

        if (pendingList.isEmpty()) {
            return;
        }

        log.info("Found {} pending raw data records to sync", pendingList.size());

        for (DeviceRawData rawData : pendingList) {
            try {
                processRawData(rawData);
            } catch (Exception e) {
                log.error("Failed to process raw data id={}: {}", rawData.getId(), e.getMessage());
            }
        }
    }

    private void processRawData(DeviceRawData rawData) {
        // Process the raw device data
        rawData.setProcessStatus(1);
        deviceRawDataMapper.updateById(rawData);
    }
}
