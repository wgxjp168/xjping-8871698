package com.health.controller;

import com.health.common.PageResult;
import com.health.common.Result;
import com.health.dto.DeviceQueryDTO;
import com.health.dto.DeviceSaveDTO;
import com.health.entity.Device;
import com.health.entity.DeviceData;
import com.health.service.DeviceService;
import com.health.vo.DeviceVO;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 设备管理接口
 */
@Api(tags = "设备管理")
@RestController
@RequestMapping("/device")
@RequiredArgsConstructor
public class DeviceController {

    private final DeviceService deviceService;

    @ApiOperation("分页查询设备列表")
    @GetMapping("/page")
    public Result<PageResult<DeviceVO>> page(DeviceQueryDTO query) {
        return Result.success(deviceService.queryPage(query));
    }

    @ApiOperation("获取设备详情")
    @GetMapping("/{id}")
    public Result<Device> getById(@PathVariable Long id) {
        return Result.success(deviceService.getById(id));
    }

    @ApiOperation("新增设备")
    @PostMapping
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Void> save(@Validated @RequestBody DeviceSaveDTO dto) {
        deviceService.save(dto);
        return Result.success();
    }

    @ApiOperation("更新设备")
    @PutMapping
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Void> update(@Validated @RequestBody DeviceSaveDTO dto) {
        if (dto.getId() == null) {
            return Result.error("设备ID不能为空");
        }
        deviceService.save(dto);
        return Result.success();
    }

    @ApiOperation("删除设备")
    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Void> delete(@PathVariable Long id) {
        deviceService.delete(id);
        return Result.success();
    }

    @ApiOperation("设备心跳上报")
    @PostMapping("/heartbeat/{deviceCode}")
    public Result<Void> heartbeat(@PathVariable String deviceCode) {
        deviceService.heartbeat(deviceCode);
        return Result.success();
    }

    @ApiOperation("设备数据上报")
    @PostMapping("/upload/{deviceCode}")
    public Result<Void> uploadData(@PathVariable String deviceCode,
                                   @RequestBody Map<String, Object> dataMap) {
        deviceService.uploadData(deviceCode, dataMap);
        return Result.success();
    }

    @ApiOperation("获取设备历史数据")
    @GetMapping("/{id}/data")
    public Result<List<DeviceData>> getDeviceData(@PathVariable Long id,
                                                   @RequestParam(defaultValue = "20") int limit) {
        return Result.success(deviceService.getDeviceData(id, limit));
    }

    @ApiOperation("获取在线设备列表")
    @GetMapping("/online")
    public Result<List<Device>> listOnlineDevices() {
        return Result.success(deviceService.listOnlineDevices());
    }
}
