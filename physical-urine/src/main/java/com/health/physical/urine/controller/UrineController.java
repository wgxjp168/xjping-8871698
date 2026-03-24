package com.health.physical.urine.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.health.physical.common.dto.Result;
import com.health.physical.urine.entity.UrineResult;
import com.health.physical.urine.mapper.UrineResultMapper;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 尿机服务控制器
 * 接收手提电脑(4G/5G)上传的优利特尿机数据
 */
@Slf4j
@Api(tags = "尿机服务 - 优利特尿机数据接收")
@RestController
@RequestMapping("/urine")
@RequiredArgsConstructor
public class UrineController {

    private final UrineResultMapper urineResultMapper;

    @ApiOperation("上传尿机检验结果（下乡手提电脑通过4G/5G上传）")
    @PostMapping("/upload")
    public Result<UrineResult> upload(@Valid @RequestBody UrineResult result) {
        // 检查是否已上传（防重复）
        UrineResult existing = urineResultMapper.selectOne(
                new LambdaQueryWrapper<UrineResult>()
                        .eq(UrineResult::getBarcode, result.getBarcode())
                        .eq(UrineResult::getDeleted, 0)
        );
        if (existing != null) {
            log.warn("尿机结果已存在，忽略重复上传: barcode={}", result.getBarcode());
            return Result.ok("结果已存在，无需重复上传", existing);
        }

        result.setUploadTime(LocalDateTime.now());
        result.setSyncStatus(0);
        result.setStatus(1);
        urineResultMapper.insert(result);
        log.info("尿机结果上传成功: barcode={}, residentId={}", result.getBarcode(), result.getResidentId());
        return Result.ok("上传成功", result);
    }

    @ApiOperation("批量上传尿机结果")
    @PostMapping("/batch-upload")
    public Result<String> batchUpload(@RequestBody List<UrineResult> results) {
        int success = 0;
        for (UrineResult result : results) {
            try {
                UrineResult existing = urineResultMapper.selectOne(
                        new LambdaQueryWrapper<UrineResult>()
                                .eq(UrineResult::getBarcode, result.getBarcode())
                                .eq(UrineResult::getDeleted, 0)
                );
                if (existing == null) {
                    result.setUploadTime(LocalDateTime.now());
                    result.setSyncStatus(0);
                    result.setStatus(1);
                    urineResultMapper.insert(result);
                    success++;
                }
            } catch (Exception e) {
                log.error("尿机结果批量上传单条失败: barcode={}, error={}", result.getBarcode(), e.getMessage());
            }
        }
        return Result.ok(String.format("批量上传完成，共%d条，成功%d条", results.size(), success));
    }

    @ApiOperation("查询体检单尿常规结果")
    @GetMapping("/physical/{physicalId}")
    public Result<List<UrineResult>> getByPhysicalId(@PathVariable Long physicalId) {
        List<UrineResult> list = urineResultMapper.selectList(
                new LambdaQueryWrapper<UrineResult>()
                        .eq(UrineResult::getPhysicalId, physicalId)
                        .eq(UrineResult::getDeleted, 0)
        );
        return Result.ok(list);
    }
}
