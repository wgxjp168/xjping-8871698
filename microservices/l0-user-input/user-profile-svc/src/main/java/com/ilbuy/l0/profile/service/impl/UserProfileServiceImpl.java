package com.ilbuy.l0.profile.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.common.core.result.ResultCode;
import com.ilbuy.l0.profile.cache.UserProfileCacheManager;
import com.ilbuy.l0.profile.domain.dto.UserProfileUpdateDTO;
import com.ilbuy.l0.profile.domain.entity.UserPreference;
import com.ilbuy.l0.profile.domain.entity.UserProfile;
import com.ilbuy.l0.profile.domain.vo.UserProfileVO;
import com.ilbuy.l0.profile.mapper.UserPreferenceMapper;
import com.ilbuy.l0.profile.mapper.UserProfileMapper;
import com.ilbuy.l0.profile.service.UserProfileService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 用户画像服务实现
 *
 * <p>数据读取采用 Cache-Aside 模式（Redis → MySQL）。
 * 写操作采用延迟双删策略保证缓存最终一致性。
 *
 * @author ILbuy Team
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class UserProfileServiceImpl implements UserProfileService {

    private final UserProfileMapper    profileMapper;
    private final UserPreferenceMapper preferenceMapper;
    private final UserProfileCacheManager cacheManager;

    // ==================== 查询 ====================

    @Override
    public UserProfileVO getProfile(Long userId) {
        validateUserId(userId);

        // 1. 先查缓存
        return cacheManager.get(userId).orElseGet(() -> {
            // 2. 缓存未命中，查 MySQL
            UserProfile profile = profileMapper.selectById(userId);
            if (profile == null) {
                throw new BizException(ResultCode.NOT_FOUND.getCode(),
                        "用户画像不存在: userId=" + userId);
            }
            List<UserPreference> preferences = preferenceMapper.selectAllByUserId(userId);

            UserProfileVO vo = toVO(profile, preferences);
            // 3. 回写缓存
            cacheManager.put(vo);
            return vo;
        });
    }

    @Override
    public UserProfileVO getProfileSummary(Long userId) {
        validateUserId(userId);
        // 摘要仅返回预算+品类，使用完整画像缓存降级
        UserProfileVO full = getProfile(userId);
        return UserProfileVO.builder()
                .userId(full.getUserId())
                .budgetMin(full.getBudgetMin())
                .budgetMax(full.getBudgetMax())
                .avgSpendMin(full.getAvgSpendMin())
                .avgSpendMax(full.getAvgSpendMax())
                .preferredCategories(full.getPreferredCategories())
                .preferredPlatforms(full.getPreferredPlatforms())
                .profileScore(full.getProfileScore())
                .build();
    }

    // ==================== 更新 ====================

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateProfile(Long userId, UserProfileUpdateDTO dto) {
        validateUserId(userId);

        UserProfile profile = profileMapper.selectById(userId);
        if (profile == null) {
            throw new BizException(ResultCode.NOT_FOUND.getCode(),
                    "用户画像不存在: userId=" + userId);
        }

        // PATCH 语义：仅更新非null字段
        LambdaUpdateWrapper<UserProfile> updateWrapper = new LambdaUpdateWrapper<UserProfile>()
                .eq(UserProfile::getUserId, userId)
                .eq(UserProfile::getDeleted, 0);

        if (dto.getGender()   != null) updateWrapper.set(UserProfile::getGender,   dto.getGender());
        if (dto.getAgeGroup() != null) updateWrapper.set(UserProfile::getAgeGroup, dto.getAgeGroup());
        if (dto.getCity()     != null) updateWrapper.set(UserProfile::getCity,     dto.getCity());
        if (dto.getBudgetMin()!= null) updateWrapper.set(UserProfile::getBudgetMin,dto.getBudgetMin());
        if (dto.getBudgetMax()!= null) updateWrapper.set(UserProfile::getBudgetMax,dto.getBudgetMax());
        if (dto.getEcoFriendly() != null) updateWrapper.set(UserProfile::getEcoFriendly, dto.getEcoFriendly());

        if (dto.getPreferredCategories() != null) {
            updateWrapper.set(UserProfile::getPreferredCategories,
                    String.join(",", dto.getPreferredCategories()));
        }
        if (dto.getSceneTags() != null) {
            updateWrapper.set(UserProfile::getSceneTags,
                    String.join(",", dto.getSceneTags()));
        }
        if (dto.getPreferredBrands() != null) {
            updateWrapper.set(UserProfile::getPreferredBrands,
                    String.join(",", dto.getPreferredBrands()));
        }
        if (dto.getPreferredPlatforms() != null) {
            updateWrapper.set(UserProfile::getPreferredPlatforms,
                    String.join(",", dto.getPreferredPlatforms()));
        }

        profileMapper.update(null, updateWrapper);

        // 刷新画像完整度
        refreshProfileScore(userId);

        // 延迟双删缓存
        cacheManager.delayedEvict(userId);

        log.info("[UserProfileService] 更新画像: userId={}", userId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updatePreferenceWeight(Long userId, String dimension,
                                       String dimensionValue, int weightDelta) {
        validateUserId(userId);

        // 查询是否已有此偏好记录
        LambdaQueryWrapper<UserPreference> query = new LambdaQueryWrapper<UserPreference>()
                .eq(UserPreference::getUserId, userId)
                .eq(UserPreference::getDimension, dimension)
                .eq(UserPreference::getDimensionValue, dimensionValue)
                .eq(UserPreference::getDeleted, 0);

        UserPreference existing = preferenceMapper.selectOne(query);

        if (existing == null) {
            // 新建偏好记录
            UserPreference newPref = new UserPreference()
                    .setUserId(userId)
                    .setDimension(dimension)
                    .setDimensionValue(dimensionValue)
                    .setWeight(Math.max(1, Math.min(100, 50 + weightDelta)))
                    .setSource("inferred")
                    .setTriggerCount(1)
                    .setLastTriggeredAt(LocalDateTime.now());
            preferenceMapper.insert(newPref);
        } else {
            // 更新权重（限制在 1-100）
            int newWeight = Math.max(1, Math.min(100, existing.getWeight() + weightDelta));
            LambdaUpdateWrapper<UserPreference> update = new LambdaUpdateWrapper<UserPreference>()
                    .eq(UserPreference::getId, existing.getId())
                    .set(UserPreference::getWeight, newWeight)
                    .set(UserPreference::getTriggerCount, existing.getTriggerCount() + 1)
                    .set(UserPreference::getLastTriggeredAt, LocalDateTime.now());
            preferenceMapper.update(null, update);
        }

        // 淘汰画像缓存（偏好变化后需刷新）
        cacheManager.evict(userId);

        log.debug("[UserProfileService] 偏好权重更新: userId={}, {}={}, delta={}",
                userId, dimension, dimensionValue, weightDelta);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void initProfile(Long userId, String nickname) {
        // 幂等：若已存在则跳过
        if (profileMapper.selectById(userId) != null) {
            log.warn("[UserProfileService] 画像已存在，跳过初始化: userId={}", userId);
            return;
        }
        UserProfile profile = new UserProfile()
                .setUserId(userId)
                .setNickname(nickname)
                .setProfileScore(0);
        profileMapper.insert(profile);
        log.info("[UserProfileService] 初始化新用户画像: userId={}", userId);
    }

    @Override
    public int refreshProfileScore(Long userId) {
        UserProfile profile = profileMapper.selectById(userId);
        if (profile == null) return 0;

        int score = 0;
        if (profile.getGender()    != null) score += 5;
        if (profile.getAgeGroup()  != null) score += 5;
        if (profile.getCity()      != null) score += 5;
        if (profile.getBudgetMax() != null) score += 20;
        if (profile.getBudgetMin() != null) score += 10;
        if (StringUtils.isNotBlank(profile.getPreferredCategories())) score += 20;
        if (StringUtils.isNotBlank(profile.getSceneTags()))           score += 10;
        if (StringUtils.isNotBlank(profile.getPreferredBrands()))     score += 15;
        if (StringUtils.isNotBlank(profile.getPreferredPlatforms()))  score += 10;

        profileMapper.updateProfileScore(userId, score);
        return score;
    }

    // ==================== 私有方法 ====================

    private UserProfileVO toVO(UserProfile profile, List<UserPreference> preferences) {
        List<UserProfileVO.PreferenceItem> prefItems = preferences == null
                ? Collections.emptyList()
                : preferences.stream()
                        .map(p -> UserProfileVO.PreferenceItem.builder()
                                .dimension(p.getDimension())
                                .dimensionValue(p.getDimensionValue())
                                .weight(p.getWeight())
                                .source(p.getSource())
                                .build())
                        .collect(Collectors.toList());

        return UserProfileVO.builder()
                .userId(profile.getUserId())
                .nickname(profile.getNickname())
                .gender(profile.getGender())
                .ageGroup(profile.getAgeGroup())
                .city(profile.getCity())
                .budgetMin(profile.getBudgetMin())
                .budgetMax(profile.getBudgetMax())
                .avgSpendMin(profile.getAvgSpendMin())
                .avgSpendMax(profile.getAvgSpendMax())
                .preferredCategories(splitToList(profile.getPreferredCategories()))
                .sceneTags(splitToList(profile.getSceneTags()))
                .preferredBrands(splitToList(profile.getPreferredBrands()))
                .preferredPlatforms(splitToList(profile.getPreferredPlatforms()))
                .purchaseFrequency(profile.getPurchaseFrequency())
                .profileScore(profile.getProfileScore())
                .preferences(prefItems)
                .build();
    }

    private List<String> splitToList(String csv) {
        if (StringUtils.isBlank(csv)) return Collections.emptyList();
        return Arrays.stream(csv.split(","))
                .map(String::trim)
                .filter(StringUtils::isNotBlank)
                .collect(Collectors.toList());
    }

    private void validateUserId(Long userId) {
        if (userId == null || userId <= 0) {
            throw new BizException(ResultCode.BAD_REQUEST.getCode(), "userId非法");
        }
    }
}
