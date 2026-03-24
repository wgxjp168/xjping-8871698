package com.health.physical.core.controller;

import com.health.physical.common.dto.PageResult;
import com.health.physical.common.dto.Result;
import com.health.physical.common.entity.PhysicalRecord;
import com.health.physical.core.entity.LabResult;
import com.health.physical.core.service.PhysicalRecordService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 体检记录管理接口
 */
@Api(tags = "体检记录管理")
@RestController
@RequestMapping("/physical")
@RequiredArgsConstructor
public class PhysicalRecordController {

    private final PhysicalRecordService physicalRecordService;

    @ApiOperation("分页查询体检记录")
    @GetMapping("/page")
    public Result<PageResult<PhysicalRecord>> pageQuery(
            @RequestParam(defaultValue = "1") int current,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String batchNo,
            @RequestParam(required = false) String orgName,
            @RequestParam(required = false) Integer status) {
        return Result.ok(PageResult.of(physicalRecordService.pageQuery(current, size, batchNo, orgName, status)));
    }

    @ApiOperation("查询体检记录详情")
    @GetMapping("/{id}")
    public Result<PhysicalRecord> getDetail(@PathVariable Long id) {
        return Result.ok(physicalRecordService.getById(id));
    }

    @ApiOperation("查询体检单检验结果")
    @GetMapping("/{id}/lab/{projectCode}")
    public Result<List<LabResult>> getLabResults(
            @PathVariable Long id,
            @PathVariable String projectCode) {
        return Result.ok(physicalRecordService.getLabResults(id, projectCode));
    }

    @ApiOperation("新建体检记录")
    @PostMapping
    public Result<PhysicalRecord> create(@RequestBody PhysicalRecord record) {
        return Result.ok("创建成功", physicalRecordService.create(record));
    }

    @ApiOperation("批量上传检验结果")
    @PostMapping("/{id}/lab/batch")
    public Result<Void> uploadLabResults(
            @PathVariable Long id,
            @RequestBody List<LabResult> results) {
        physicalRecordService.uploadLabResults(id, results);
        return Result.ok("检验结果上传成功，共" + results.size() + "条");
    }

    @ApiOperation("完成体检（触发同步）")
    @PostMapping("/{id}/complete")
    public Result<Void> complete(
            @PathVariable Long id,
            @RequestHeader(value = "X-Doc-Id", defaultValue = "") String docId) {
        physicalRecordService.complete(id, docId);
        return Result.ok("体检已完成");
    }
}
