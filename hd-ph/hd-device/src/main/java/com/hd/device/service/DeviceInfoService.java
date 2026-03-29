package com.hd.device.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.hd.device.entity.DeviceInfo;
import com.hd.device.mapper.DeviceInfoMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class DeviceInfoService {

    @Autowired
    private DeviceInfoMapper deviceInfoMapper;

    public List<DeviceInfo> listAll() {
        return deviceInfoMapper.selectList(
                new LambdaQueryWrapper<DeviceInfo>().eq(DeviceInfo::getDeleted, 0)
        );
    }

    public DeviceInfo getById(Long id) {
        return deviceInfoMapper.selectById(id);
    }

    public void create(DeviceInfo device) {
        deviceInfoMapper.insert(device);
    }

    public void update(DeviceInfo device) {
        deviceInfoMapper.updateById(device);
    }

    public long countOnline() {
        return deviceInfoMapper.selectCount(
                new LambdaQueryWrapper<DeviceInfo>()
                        .eq(DeviceInfo::getStatus, 1)
                        .eq(DeviceInfo::getDeleted, 0)
        );
    }

    public void delete(Long id) {
        DeviceInfo d = new DeviceInfo();
        d.setId(id);
        d.setDeleted(1);
        deviceInfoMapper.updateById(d);
    }
}
