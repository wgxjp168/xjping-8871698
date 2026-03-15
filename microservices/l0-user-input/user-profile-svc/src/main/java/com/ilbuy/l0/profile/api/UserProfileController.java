package com.ilbuy.l0.profile.api;

import com.ilbuy.common.core.result.Result;
import com.ilbuy.common.security.context.SecurityUtils;
import com.ilbuy.l0.profile.domain.dto.UserProfileUpdateDTO;
import com.ilbuy.l0.profile.domain.vo.UserProfileVO;
import com.ilbuy.l0.profile.service.UserProfileService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

/**
 * 用户画像 API
 *
 * <p>提供用户画像的完整 CRUD，同时暴露 summary 接口供
 * multimodal-input-svc 通过 Feign 快速获取预算/偏好摘要。
 *
 * <p>与上下游对接接口预留：
 * <ul>
 *   <li>L1/L2 调用：GET /api/v0/profiles/{userId}/summary 获取画像摘要</li>
 *   <li>L5 业务层调用：POST /api/v0/profiles/{userId}/preference 行为驱动更新权重</li>
 * </ul>
 *
 * @author ILbuy Team
 */
@Slf4j
@RestController
@RequestMapping("/api/v0/profiles")
@RequiredArgsConstructor
@Tag(name = "L0-用户画像", description = "用户历史偏好/预算/场景画像管理")
@SecurityRequirement(name = "BearerAuth")
public class UserProfileController {

    private final UserProfileService userProfileService;

    /**
     * 获取当前登录用户的完整画像
     */
    @GetMapping("/me")
    @Operation(summary = "获取当前用户完整画像")
    @PreAuthorize("isAuthenticated()")
    public Result<UserProfileVO> getMyProfile() {
        Long userId = SecurityUtils.currentUserId();
        return Result.ok(userProfileService.getProfile(userId));
    }

    /**
     * 获取指定用户完整画像（管理员或本人）
     */
    @GetMapping("/{userId}")
    @Operation(summary = "获取指定用户完整画像（需管理员权限）")
    @PreAuthorize("hasRole('ADMIN') or #userId == @securityUtils.currentUserId()")
    public Result<UserProfileVO> getProfile(
            @Parameter(description = "用户ID") @PathVariable Long userId) {
        return Result.ok(userProfileService.getProfile(userId));
    }

    /**
     * 获取用户画像摘要（供 multimodal-input-svc Feign 调用）
     * 仅返回预算区间 + 偏好品类，响应更快
     */
    @GetMapping("/{userId}/summary")
    @Operation(summary = "获取用户画像摘要", description = "供内部服务快速获取，仅含预算+品类")
    @PreAuthorize("isAuthenticated()")
    public Result<UserProfileVO> getProfileSummary(
            @Parameter(description = "用户ID") @PathVariable Long userId) {
        return Result.ok(userProfileService.getProfileSummary(userId));
    }

    /**
     * 更新当前用户画像（PATCH语义）
     */
    @PutMapping("/me")
    @Operation(summary = "更新当前用户画像")
    @PreAuthorize("isAuthenticated()")
    public Result<Void> updateMyProfile(@Valid @RequestBody UserProfileUpdateDTO dto) {
        Long userId = SecurityUtils.currentUserId();
        userProfileService.updateProfile(userId, dto);
        return Result.ok();
    }

    /**
     * 行为驱动的偏好权重更新（供 L5 业务层调用）
     */
    @PostMapping("/{userId}/preference")
    @Operation(summary = "行为驱动偏好权重更新", description = "用户行为后由L5业务层调用")
    @PreAuthorize("hasRole('INTERNAL') or hasRole('ADMIN')")
    public Result<Void> updatePreference(
            @PathVariable Long userId,
            @RequestParam String dimension,
            @RequestParam String dimensionValue,
            @RequestParam(defaultValue = "5") int weightDelta) {
        userProfileService.updatePreferenceWeight(userId, dimension, dimensionValue, weightDelta);
        return Result.ok();
    }

    /**
     * 初始化新用户画像（用户注册后由 auth-svc 调用）
     */
    @PostMapping("/{userId}/init")
    @Operation(summary = "初始化用户画像", description = "注册成功后由auth-svc调用")
    @PreAuthorize("hasRole('INTERNAL')")
    public Result<Void> initProfile(
            @PathVariable Long userId,
            @RequestParam String nickname) {
        userProfileService.initProfile(userId, nickname);
        return Result.ok();
    }

    /**
     * 重新计算画像完整度分
     */
    @PostMapping("/{userId}/refresh-score")
    @Operation(summary = "刷新画像完整度分")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Integer> refreshScore(@PathVariable Long userId) {
        return Result.ok(userProfileService.refreshProfileScore(userId));
    }
}
