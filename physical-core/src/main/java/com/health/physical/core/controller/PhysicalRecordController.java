package com.health.physical.core.controller;

import com.health.physical.common.dto.PageResult;
import com.health.physical.common.dto.Result;
import com.health.physical.common.entity.PhysicalRecord;
import com.health.physical.core.entity.LabResult;
import com.health.physical.core.mapper.LabResultMapper;
import com.health.physical.core.mapper.PhysicalRecordMapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
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

    private final PhysicalRecordMapper physicalRecordMapper;
    private final LabResultMapper labResultMapper;

    @ApiOperation("分页查询体检记录")
    @GetMapping("/page")
    public Result<PageResult<PhysicalRecord>> pageQuery(
            @RequestParam(defaultValue = "1") int current,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String batchNo,
            @RequestParam(required = false) String orgName,
            @RequestParam(required = false) Integer status) {
        Page<PhysicalRecord> page = new Page<>(current, size);
        physicalRecordMapper.selectPageWithResident(page, batchNo, orgName, status);
        return Result.ok(PageResult.of(page));
    }

    @ApiOperation("查询体检记录详情（含检验结果）")
    @GetMapping("/{id}")
    public Result<PhysicalRecord> getDetail(@PathVariable Long id) {
        PhysicalRecord record = physicalRecordMapper.selectById(id);
        if (record == null) {
            return Result.fail(404, "体检记录不存在");
        }
        return Result.ok(record);
    }

    @ApiOperation("查询体检记录检验结果")
    @GetMapping("/{id}/lab/{projectCode}")
    public Result<List<LabResult>> getLabResults(
            @PathVariable Long id,
            @PathVariable String projectCode) {
        List<LabResult> results = labResultMapper.selectByPhysicalIdAndProject(id, projectCode);
        return Result.ok(results);
    }

    @ApiOperation("新建体检记录")
    @PostMapping
    public Result<PhysicalRecord> create(@RequestBody PhysicalRecord record) {
        record.setSyncStatus(0);
        record.setStatus(1);
        physicalRecordMapper.insert(record);
        return Result.ok("创建成功", record);
    }

    @ApiOperation("上传检验结果（批量）")
    @PostMapping("/{id}/lab/batch")
    public Result<Void> uploadLabResults(
            @PathVariable Long id,
            @RequestBody List<LabResult> results) {
        results.forEach(r -> r.setPhysicalId(id));
        if (!results.isEmpty()) {
            labResultMapper.batchInsertOrUpdate(results);
        }
        return Result.ok("检验结果上传成功，共" + results.size() + "条");
    }
}
