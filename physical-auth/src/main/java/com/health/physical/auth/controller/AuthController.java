package com.health.physical.auth.controller;

import com.github.xiaoymin.knife4j.annotations.ApiOperationSupport;
import com.health.physical.auth.dto.LoginRequest;
import com.health.physical.auth.dto.LoginResponse;
import com.health.physical.auth.dto.PermCheckRequest;
import com.health.physical.auth.entity.DocPermission;
import com.health.physical.auth.entity.Doctor;
import com.health.physical.auth.service.AuthService;
import com.health.physical.common.constant.PermissionConstants;
import com.health.physical.common.dto.Result;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
import java.util.List;

/**
 * 权限服务 - 登录/权限校验控制器
 */
@Api(tags = "权限服务 - 医生认证与权限管控")
@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @ApiOperation("医生登录（网页端/移动端统一入口）")
    @ApiOperationSupport(order = 1)
    @PostMapping("/login")
    public Result<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        LoginResponse response = authService.login(request);
        return Result.ok("登录成功", response);
    }

    @ApiOperation("退出登录")
    @ApiOperationSupport(order = 2)
    @PostMapping("/logout")
    public Result<Void> logout(
            @ApiParam("Bearer Token") @RequestHeader(PermissionConstants.TOKEN_HEADER) String authorization) {
        String token = authorization.replace(PermissionConstants.TOKEN_PREFIX, "");
        authService.logout(token);
        return Result.ok("退出成功");
    }

    @ApiOperation("校验权限（内部接口，供其他服务调用）")
    @ApiOperationSupport(order = 3)
    @PostMapping("/check")
    public Result<Boolean> checkPermission(@Valid @RequestBody PermCheckRequest request) {
        boolean hasPermission = authService.checkPermission(request);
        return Result.ok(hasPermission);
    }

    @ApiOperation("获取医生全部权限列表")
    @ApiOperationSupport(order = 4)
    @GetMapping("/permissions/{docId}")
    public Result<List<DocPermission>> getDoctorPermissions(
            @ApiParam("医生ID") @PathVariable String docId) {
        List<DocPermission> permissions = authService.getDoctorPermissions(docId);
        return Result.ok(permissions);
    }

    @ApiOperation("Token校验（网关调用）")
    @ApiOperationSupport(order = 5)
    @GetMapping("/validate")
    public Result<Doctor> validateToken(
            @ApiParam("Bearer Token") @RequestHeader(PermissionConstants.TOKEN_HEADER) String authorization) {
        String token = authorization.replace(PermissionConstants.TOKEN_PREFIX, "");
        Doctor doctor = authService.validateToken(token);
        return Result.ok(doctor);
    }

    @ApiOperation("授予权限")
    @ApiOperationSupport(order = 6)
    @PostMapping("/grant")
    public Result<Void> grantPermission(
            @RequestBody DocPermission permission,
            @RequestHeader("X-Operator-Id") String operatorId) {
        authService.grantPermission(permission, operatorId);
        return Result.ok("授权成功");
    }

    @ApiOperation("撤销权限")
    @ApiOperationSupport(order = 7)
    @DeleteMapping("/revoke/{permissionId}")
    public Result<Void> revokePermission(
            @PathVariable Long permissionId,
            @RequestHeader("X-Operator-Id") String operatorId) {
        authService.revokePermission(permissionId, operatorId);
        return Result.ok("撤权成功");
    }

    @ApiOperation("手动触发县域账号同步")
    @ApiOperationSupport(order = 8)
    @PostMapping("/sync/county")
    public Result<Void> syncFromCounty() {
        authService.syncFromCounty();
        return Result.ok("同步已触发，请稍候");
    }
}
