package com.health.physical.urine.controller;

import com.health.physical.common.dto.Result;
import com.health.physical.urine.entity.UrineResult;
import com.health.physical.urine.service.UrineService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
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

    private final UrineService urineService;

    @ApiOperation("上传尿机检验结果（下乡手提电脑通过4G/5G上传）")
    @PostMapping("/upload")
    public Result<UrineResult> upload(@Valid @RequestBody UrineResult result) {
        return Result.ok("上传成功", urineService.upload(result));
    }

    @ApiOperation("批量上传尿机结果")
    @PostMapping("/batch-upload")
    public Result<String> batchUpload(@RequestBody List<UrineResult> results) {
        int success = urineService.batchUpload(results);
        return Result.ok(String.format("批量上传完成，共%d条，成功%d条", results.size(), success));
    }

    @ApiOperation("查询体检单尿常规结果")
    @GetMapping("/physical/{physicalId}")
    public Result<List<UrineResult>> getByPhysicalId(@PathVariable Long physicalId) {
        return Result.ok(urineService.getByPhysicalId(physicalId));
    }

    @ApiOperation("按条码查询尿机结果")
    @GetMapping("/barcode/{barcode}")
    public Result<UrineResult> getByBarcode(@PathVariable String barcode) {
        UrineResult result = urineService.getByBarcode(barcode);
        if (result == null) {
            return Result.fail(404, "条码不存在: " + barcode);
        }
        return Result.ok(result);
    }
}
