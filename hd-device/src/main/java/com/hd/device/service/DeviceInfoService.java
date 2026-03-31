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
        LambdaQueryWrapper<DeviceInfo> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(DeviceInfo::getDeleted, 0);
        return deviceInfoMapper.selectList(wrapper);
    }

    public long countOnline() {
        LambdaQueryWrapper<DeviceInfo> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(DeviceInfo::getStatus, "ONLINE");
        wrapper.eq(DeviceInfo::getDeleted, 0);
        return deviceInfoMapper.selectCount(wrapper);
    }
}
