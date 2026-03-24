package com.health.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.health.dto.DeviceQueryDTO;
import com.health.entity.Device;
import com.health.vo.DeviceVO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * 设备 Mapper
 */
@Mapper
public interface DeviceMapper extends BaseMapper<Device> {

    Page<DeviceVO> queryDevicePage(Page<DeviceVO> page, @Param("query") DeviceQueryDTO query);
}
