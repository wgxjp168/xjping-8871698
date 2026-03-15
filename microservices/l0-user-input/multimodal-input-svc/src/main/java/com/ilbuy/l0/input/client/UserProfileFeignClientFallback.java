package com.ilbuy.l0.input.client;

import com.ilbuy.common.core.result.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * UserProfileFeignClient 降级实现
 *
 * <p>当 user-profile-svc 不可用时（超时/503/网络异常），
 * 返回空画像摘要（不影响输入解析主流程，仅丢失预算辅助增强）。
 *
 * @author ILbuy Team
 */
@Slf4j
@Component
public class UserProfileFeignClientFallback implements UserProfileFeignClient {

    @Override
    public Result<UserProfileSummary> getUserSummary(Long userId) {
        log.warn("[UserProfileFallback] user-profile-svc 不可用，返回空画像: userId={}", userId);
        return Result.success(null);
    }
}
