package com.ilbuy.l0.input.client;

import com.ilbuy.common.core.result.Result;
import com.ilbuy.l0.input.domain.dto.ParsedInput;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

/**
 * 用户画像服务 Feign 客户端
 *
 * <p>L0 multimodal-input-svc → user-profile-svc 的内部调用接口，
 * 用于在解析输入时补充用户历史偏好/预算/场景信息，
 * 增强 ParsedInput 的上下文完整性供 L1 网关消费。
 *
 * @author ILbuy Team
 */
@FeignClient(
        name = "user-profile-svc",
        contextId = "userProfileFeignClient",
        path = "/api/v0/profiles",
        fallback = UserProfileFeignClientFallback.class
)
public interface UserProfileFeignClient {

    /**
     * 获取用户画像摘要（预算区间 + 偏好品类）
     *
     * @param userId 用户ID
     * @return 用户画像 VO
     */
    @GetMapping("/{userId}/summary")
    Result<UserProfileSummary> getUserSummary(@PathVariable("userId") Long userId);

    /**
     * 用户画像摘要（内嵌 DTO，避免跨服务引入整体依赖）
     */
    record UserProfileSummary(
            Long userId,
            java.math.BigDecimal budgetMin,
            java.math.BigDecimal budgetMax,
            java.util.List<String> preferredCategories,
            String preferredScene
    ) {}
}
