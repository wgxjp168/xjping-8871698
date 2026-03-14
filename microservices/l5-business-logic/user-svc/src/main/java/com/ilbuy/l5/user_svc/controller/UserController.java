package com.ilbuy.l5.user_svc.controller;

import com.ilbuy.common.core.Result;
import com.ilbuy.l5.user_svc.service.UserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

/**
 * 用户管理接口
 */
@Tag(name = "用户管理", description = "用户注册/登录/画像管理")
@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    @Operation(summary = "用户注册")
    @PostMapping("/register")
    public Result<?> register(@RequestBody RegisterRequest request) {
        return Result.ok(userService.register(request));
    }

    @Operation(summary = "用户登录")
    @PostMapping("/login")
    public Result<?> login(@RequestBody LoginRequest request) {
        return Result.ok(userService.login(request));
    }

    @Operation(summary = "获取用户信息")
    @GetMapping("/{userId}")
    public Result<?> getUserInfo(@PathVariable Long userId) {
        return Result.ok(userService.getUserInfo(userId));
    }

    @Operation(summary = "更新用户画像")
    @PutMapping("/{userId}/profile")
    public Result<?> updateProfile(
            @PathVariable Long userId,
            @RequestBody UpdateProfileRequest request) {
        userService.updateProfile(userId, request);
        return Result.ok();
    }

    @Operation(summary = "刷新Token")
    @PostMapping("/token/refresh")
    public Result<?> refreshToken(@RequestHeader("Refresh-Token") String refreshToken) {
        return Result.ok(userService.refreshToken(refreshToken));
    }

    // 内部DTO类（实际项目中放独立文件）
    public record RegisterRequest(
            String username, String password, String phone,
            String email, String userType, String companyName
    ) {}

    public record LoginRequest(String username, String password) {}

    public record UpdateProfileRequest(
            String nickname, String industry, String budgetRange,
            String preferredCategories
    ) {}
}
