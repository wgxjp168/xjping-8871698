package com.ilbuy.l0.profile.service;

import com.ilbuy.l0.profile.domain.dto.UserProfileUpdateDTO;
import com.ilbuy.l0.profile.domain.vo.UserProfileVO;

/**
 * 用户画像服务接口
 *
 * <p>提供用户画像的查询、更新、偏好权重更新等核心业务能力，
 * 所有读操作优先从 Redis 缓存获取（Cache-Aside 模式）。
 *
 * @author ILbuy Team
 */
public interface UserProfileService {

    /**
     * 获取完整用户画像（含偏好明细）
     * 优先读 Redis 缓存，缓存 TTL=30min
     *
     * @param userId 用户ID
     * @return 用户画像 VO
     */
    UserProfileVO getProfile(Long userId);

    /**
     * 获取用户画像摘要（仅预算+偏好品类，供 multimodal-input-svc 快速消费）
     *
     * @param userId 用户ID
     * @return 画像摘要 VO
     */
    UserProfileVO getProfileSummary(Long userId);

    /**
     * 更新用户画像（PATCH语义，仅更新非null字段）
     * 更新后主动淘汰 Redis 缓存
     *
     * @param userId    用户ID
     * @param updateDTO 更新内容
     */
    void updateProfile(Long userId, UserProfileUpdateDTO updateDTO);

    /**
     * 行为驱动的偏好权重更新
     * 例如：用户购买了"华为"手机后，调用此接口增强 brand=华为 的权重
     *
     * @param userId         用户ID
     * @param dimension      维度（category/brand/platform/scene）
     * @param dimensionValue 维度值
     * @param weightDelta    权重增量（可为负）
     */
    void updatePreferenceWeight(Long userId, String dimension,
                                String dimensionValue, int weightDelta);

    /**
     * 初始化新用户画像（注册后调用）
     *
     * @param userId   用户ID
     * @param nickname 昵称
     */
    void initProfile(Long userId, String nickname);

    /**
     * 重新计算并刷新画像完整度分
     *
     * @param userId 用户ID
     * @return 最新分数（0-100）
     */
    int refreshProfileScore(Long userId);
}
