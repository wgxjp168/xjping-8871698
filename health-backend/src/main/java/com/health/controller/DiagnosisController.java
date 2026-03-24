package com.health.controller;

import com.health.common.PageResult;
import com.health.common.Result;
import com.health.dto.DiagnosisQueryDTO;
import com.health.dto.DiagnosisSaveDTO;
import com.health.service.DiagnosisService;
import com.health.vo.DiagnosisVO;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

/**
 * 诊断报告接口
 */
@Api(tags = "诊断管理")
@RestController
@RequestMapping("/diagnosis")
@RequiredArgsConstructor
public class DiagnosisController {

    private final DiagnosisService diagnosisService;

    @ApiOperation("分页查询诊断报告")
    @GetMapping("/page")
    public Result<PageResult<DiagnosisVO>> page(DiagnosisQueryDTO query) {
        return Result.success(diagnosisService.queryPage(query));
    }

    @ApiOperation("获取诊断报告详情")
    @GetMapping("/{id}")
    public Result<DiagnosisVO> detail(@PathVariable Long id) {
        return Result.success(diagnosisService.getDetail(id));
    }

    @ApiOperation("保存诊断报告")
    @PostMapping
    @PreAuthorize("hasAnyRole('ADMIN','DOCTOR')")
    public Result<Void> save(@Validated @RequestBody DiagnosisSaveDTO dto,
                             Authentication authentication) {
        // TODO: 从认证上下文获取 doctorId 和 patientId
        diagnosisService.save(dto, 1L, dto.getOrderId());
        return Result.success();
    }

    @ApiOperation("确认诊断报告")
    @PutMapping("/{id}/confirm")
    @PreAuthorize("hasAnyRole('ADMIN','DOCTOR')")
    public Result<Void> confirm(@PathVariable Long id) {
        diagnosisService.confirm(id);
        return Result.success();
    }

    @ApiOperation("发布诊断报告")
    @PutMapping("/{id}/publish")
    @PreAuthorize("hasAnyRole('ADMIN','DOCTOR')")
    public Result<Void> publish(@PathVariable Long id) {
        diagnosisService.publish(id);
        return Result.success();
    }

    @ApiOperation("删除诊断报告")
    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Void> delete(@PathVariable Long id) {
        diagnosisService.delete(id);
        return Result.success();
    }
}
