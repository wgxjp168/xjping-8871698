package com.health.physical.sync.controller;

import com.health.physical.common.dto.Result;
import com.health.physical.sync.service.CountySyncService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 同步服务控制器
 */
@Api(tags = "同步服务 - 县域数据同步")
@RestController
@RequestMapping("/sync")
@RequiredArgsConstructor
public class SyncController {

    private final CountySyncService countySyncService;

    @ApiOperation("手动触发体检数据同步")
    @PostMapping("/physical/trigger")
    public Result<Void> triggerSync() {
        countySyncService.batchSyncPhysicalToCounty();
        return Result.ok("同步已完成");
    }
}
