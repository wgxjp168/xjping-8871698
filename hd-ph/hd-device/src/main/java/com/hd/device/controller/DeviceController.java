package com.hd.device.controller;

import com.hd.common.result.Result;
import com.hd.device.entity.DeviceInfo;
import com.hd.device.entity.DeviceRawData;
import com.hd.device.service.CheckResultSyncService;
import com.hd.device.service.DeviceDataService;
import com.hd.device.service.DeviceInfoService;
import com.hd.device.service.PublicHealthUploadService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/devices")
public class DeviceController {

    @Autowired
    private DeviceInfoService deviceInfoService;

    @Autowired
    private DeviceDataService deviceDataService;

    @Autowired
    private CheckResultSyncService syncService;

    @Autowired
    private PublicHealthUploadService uploadService;

    /** 手动触发同步（device_raw_data → check_result） */
    @PostMapping("/sync")
    public Result<String> manualSync() {
        syncService.syncPendingResults();
        return Result.success("同步完成");
    }

    /** 手动上传单个体检单结果到公卫平台 */
    @PostMapping("/upload/{orderNo}")
    public Result<String> uploadOrder(@PathVariable String orderNo) {
        boolean ok = uploadService.uploadByOrderNo(orderNo);
        return ok ? Result.success("上传成功") : Result.error("上传失败，请检查公卫平台配置");
    }

    @GetMapping
    public Result<List<DeviceInfo>> list() {
        return Result.success(deviceInfoService.listAll());
    }

    @GetMapping("/{id}")
    public Result<DeviceInfo> getById(@PathVariable Long id) {
        return Result.success(deviceInfoService.getById(id));
    }

    @PostMapping
    public Result<Void> create(@RequestBody DeviceInfo device) {
        deviceInfoService.create(device);
        return Result.success(null);
    }

    @PutMapping("/{id}")
    public Result<Void> update(@PathVariable Long id, @RequestBody DeviceInfo device) {
        device.setId(id);
        deviceInfoService.update(device);
        return Result.success(null);
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        deviceInfoService.delete(id);
        return Result.success(null);
    }

    @GetMapping("/pending-data")
    public Result<List<DeviceRawData>> pendingData() {
        return Result.success(deviceDataService.listPendingData());
    }

    @PutMapping("/raw-data/{id}/processed")
    public Result<Void> markProcessed(@PathVariable Long id) {
        deviceDataService.markProcessed(id);
        return Result.success(null);
    }

    @GetMapping("/health")
    public Result<String> health() {
        return Result.success("hd-device OK");
    }
}
