package com.health.physical.dr.controller;

import com.github.xiaoymin.knife4j.annotations.ApiOperationSupport;
import com.health.physical.common.constant.PermissionConstants;
import com.health.physical.common.dto.PageResult;
import com.health.physical.common.dto.Result;
import com.health.physical.common.exception.BusinessException;
import com.health.physical.common.util.JwtUtil;
import com.health.physical.dr.dto.DrScanRequest;
import com.health.physical.dr.dto.DrScanResponse;
import com.health.physical.dr.dto.DrSubmitRequest;
import com.health.physical.dr.entity.DrRecord;
import com.health.physical.dr.service.DrService;
import io.jsonwebtoken.Claims;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;

/**
 * DR服务控制器
 */
@Api(tags = "DR服务 - DR条码/检查记录/县域同步")
@RestController
@RequestMapping("/dr")
@RequiredArgsConstructor
public class DrController {

    private final DrService drService;

    @Value("${jwt.secret:physical_health_system_jwt_secret_key_2024_secure_enough}")
    private String jwtSecret;

    @ApiOperation("DR条码扫描（院内扫码枪扫描DR条码，带出居民信息）")
    @ApiOperationSupport(order = 1)
    @PostMapping("/scan")
    public Result<DrScanResponse> scanDrBarcode(
            @Valid @RequestBody DrScanRequest request,
            @RequestHeader(PermissionConstants.TOKEN_HEADER) String authorization) {
        String doctorId = extractDoctorId(authorization);
        DrScanResponse response = drService.scanDrBarcode(request, doctorId);
        return Result.ok(response);
    }

    @ApiOperation("提交DR检查结果（检查完成后提交结果，自动同步县域）")
    @ApiOperationSupport(order = 2)
    @PostMapping("/submit")
    public Result<Void> submitDrResult(
            @Valid @RequestBody DrSubmitRequest request,
            @RequestHeader(PermissionConstants.TOKEN_HEADER) String authorization) {
        String doctorId = extractDoctorId(authorization);
        drService.submitDrResult(request, doctorId);
        return Result.ok("DR检查结果提交成功，已触发同步");
    }

    @ApiOperation("县域开单注册（县域系统回调，在院内预注册DR条码）")
    @ApiOperationSupport(order = 3)
    @PostMapping("/register")
    public Result<DrRecord> registerDrOrder(@RequestBody DrRecord drRecord) {
        DrRecord saved = drService.registerDrOrder(drRecord);
        return Result.ok("DR开单注册成功", saved);
    }

    @ApiOperation("分页查询DR记录")
    @ApiOperationSupport(order = 4)
    @GetMapping("/page")
    public Result<PageResult<DrRecord>> pageQuery(
            @ApiParam("当前页") @RequestParam(defaultValue = "1") int current,
            @ApiParam("每页大小") @RequestParam(defaultValue = "20") int size,
            @ApiParam("体检批次号") @RequestParam(required = false) String batchNo,
            @ApiParam("检查医生ID") @RequestParam(required = false) String examDoctorId,
            @ApiParam("状态 0待检查/1检查中/2已完成/3已同步/4已取消") @RequestParam(required = false) Integer status,
            @ApiParam("开始日期 yyyy-MM-dd") @RequestParam(required = false) String startDate,
            @ApiParam("结束日期 yyyy-MM-dd") @RequestParam(required = false) String endDate) {
        PageResult<DrRecord> result = drService.pageQuery(current, size, batchNo, examDoctorId, status, startDate, endDate);
        return Result.ok(result);
    }

    @ApiOperation("查询DR记录详情")
    @ApiOperationSupport(order = 5)
    @GetMapping("/{id}")
    public Result<DrRecord> getDetail(@PathVariable Long id) {
        return Result.ok(drService.getDetail(id));
    }

    @ApiOperation("手动同步DR结果至县域")
    @ApiOperationSupport(order = 6)
    @PostMapping("/sync/{id}")
    public Result<Void> syncToCounty(@PathVariable Long id) {
        drService.syncToCounty(id);
        return Result.ok("同步已触发");
    }

    private String extractDoctorId(String authorization) {
        String token = authorization.replace(PermissionConstants.TOKEN_PREFIX, "");
        Claims claims = JwtUtil.parseToken(token, jwtSecret);
        if (claims == null) {
            throw BusinessException.unauthorized("Token无效或已过期");
        }
        return (String) claims.get("docId");
    }
}
