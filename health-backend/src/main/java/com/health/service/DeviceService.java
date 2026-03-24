package com.health.service;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.health.common.PageResult;
import com.health.common.exception.BusinessException;
import com.health.dto.DeviceQueryDTO;
import com.health.dto.DeviceSaveDTO;
import com.health.entity.Device;
import com.health.entity.DeviceData;
import com.health.mapper.DeviceDataMapper;
import com.health.mapper.DeviceMapper;
import com.health.vo.DeviceVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * 设备服务
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DeviceService {

    private final DeviceMapper deviceMapper;
    private final DeviceDataMapper deviceDataMapper;

    public PageResult<DeviceVO> queryPage(DeviceQueryDTO query) {
        Page<DeviceVO> page = new Page<>(query.getPageNum(), query.getPageSize());
        deviceMapper.queryDevicePage(page, query);
        return PageResult.of(page);
    }

    public Device getById(Long id) {
        Device device = deviceMapper.selectById(id);
        if (device == null) {
            throw new BusinessException("设备不存在");
        }
        return device;
    }

    @Transactional
    public void save(DeviceSaveDTO dto) {
        // 检查编码唯一性
        LambdaQueryWrapper<Device> wrapper = new LambdaQueryWrapper<Device>()
                .eq(Device::getCode, dto.getCode())
                .eq(Device::getDeleted, 0);
        if (dto.getId() != null) {
            wrapper.ne(Device::getId, dto.getId());
        }
        if (deviceMapper.selectCount(wrapper) > 0) {
            throw new BusinessException("设备编码已存在");
        }

        Device device = new Device();
        BeanUtil.copyProperties(dto, device);
        if (device.getId() == null) {
            device.setStatus("OFFLINE");
            deviceMapper.insert(device);
        } else {
            deviceMapper.updateById(device);
        }
    }

    @Transactional
    public void delete(Long id) {
        Device device = getById(id);
        deviceMapper.deleteById(device.getId());
    }

    /**
     * 设备心跳上报
     */
    @Transactional
    public void heartbeat(String deviceCode) {
        Device device = deviceMapper.selectOne(
                new LambdaQueryWrapper<Device>().eq(Device::getCode, deviceCode)
        );
        if (device == null) {
            throw new BusinessException("设备不存在: " + deviceCode);
        }
        device.setStatus("ONLINE");
        device.setLastHeartbeat(LocalDateTime.now());
        deviceMapper.updateById(device);
    }

    /**
     * 设备数据上报
     */
    @Transactional
    public void uploadData(String deviceCode, Map<String, Object> dataMap) {
        Device device = deviceMapper.selectOne(
                new LambdaQueryWrapper<Device>().eq(Device::getCode, deviceCode)
        );
        if (device == null) {
            throw new BusinessException("设备不存在: " + deviceCode);
        }

        DeviceData data = new DeviceData();
        data.setDeviceId(device.getId());
        data.setDeviceCode(deviceCode);
        data.setValue(String.valueOf(dataMap.getOrDefault("value", "")));
        data.setUnit(String.valueOf(dataMap.getOrDefault("unit", "")));
        data.setItemCode(String.valueOf(dataMap.getOrDefault("itemCode", "")));
        data.setMeasureTime(LocalDateTime.now());
        data.setStatus("PENDING");
        if (dataMap.containsKey("orderId")) {
            data.setOrderId(Long.valueOf(dataMap.get("orderId").toString()));
        }
        if (dataMap.containsKey("patientId")) {
            data.setPatientId(Long.valueOf(dataMap.get("patientId").toString()));
        }
        deviceDataMapper.insert(data);

        log.info("设备[{}]数据上报成功: {}", deviceCode, dataMap);
    }

    public List<DeviceData> getDeviceData(Long deviceId, int limit) {
        return deviceDataMapper.selectList(
                new LambdaQueryWrapper<DeviceData>()
                        .eq(DeviceData::getDeviceId, deviceId)
                        .orderByDesc(DeviceData::getCreateTime)
                        .last("LIMIT " + limit)
        );
    }

    /**
     * 定时检查设备在线状态 (每60秒)
     */
    @Scheduled(fixedDelay = 60000)
    public void checkDeviceStatus() {
        LocalDateTime timeout = LocalDateTime.now().minusSeconds(60);
        List<Device> onlineDevices = deviceMapper.selectList(
                new LambdaQueryWrapper<Device>().eq(Device::getStatus, "ONLINE")
        );
        for (Device device : onlineDevices) {
            if (device.getLastHeartbeat() != null && device.getLastHeartbeat().isBefore(timeout)) {
                device.setStatus("OFFLINE");
                deviceMapper.updateById(device);
                log.warn("设备[{}]心跳超时，已标记为离线", device.getCode());
            }
        }
    }

    public List<Device> listOnlineDevices() {
        return deviceMapper.selectList(
                new LambdaQueryWrapper<Device>().eq(Device::getStatus, "ONLINE").eq(Device::getDeleted, 0)
        );
    }
}
