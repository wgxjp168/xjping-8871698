package com.ilbuy.l0.profile.service;

import com.ilbuy.common.core.exception.BizException;
import com.ilbuy.l0.profile.cache.UserProfileCacheManager;
import com.ilbuy.l0.profile.domain.dto.UserProfileUpdateDTO;
import com.ilbuy.l0.profile.domain.entity.UserPreference;
import com.ilbuy.l0.profile.domain.entity.UserProfile;
import com.ilbuy.l0.profile.domain.vo.UserProfileVO;
import com.ilbuy.l0.profile.mapper.UserPreferenceMapper;
import com.ilbuy.l0.profile.mapper.UserProfileMapper;
import com.ilbuy.l0.profile.service.impl.UserProfileServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * UserProfileService 单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("UserProfileService - 用户画像服务测试")
class UserProfileServiceTest {

    @Mock private UserProfileMapper    profileMapper;
    @Mock private UserPreferenceMapper preferenceMapper;
    @Mock private UserProfileCacheManager cacheManager;

    private UserProfileService service;

    @BeforeEach
    void setUp() {
        service = new UserProfileServiceImpl(profileMapper, preferenceMapper, cacheManager);
    }

    // ==================== 查询测试 ====================

    @Nested
    @DisplayName("getProfile - 获取用户画像")
    class GetProfileTests {

        @Test
        @DisplayName("缓存命中时直接返回缓存数据")
        void returnsCachedProfile() {
            UserProfileVO cached = UserProfileVO.builder()
                    .userId(1L)
                    .nickname("测试用户")
                    .budgetMax(new BigDecimal("5000"))
                    .build();
            when(cacheManager.get(1L)).thenReturn(Optional.of(cached));

            UserProfileVO result = service.getProfile(1L);

            assertThat(result.getUserId()).isEqualTo(1L);
            assertThat(result.getNickname()).isEqualTo("测试用户");
            // 缓存命中时不查DB
            verifyNoInteractions(profileMapper);
        }

        @Test
        @DisplayName("缓存未命中时查MySQL并回写缓存")
        void queriesDbOnCacheMiss() {
            when(cacheManager.get(1L)).thenReturn(Optional.empty());

            UserProfile profile = new UserProfile()
                    .setUserId(1L)
                    .setNickname("MySQL用户")
                    .setBudgetMax(new BigDecimal("8000"))
                    .setPreferredCategories("手机,电脑")
                    .setProfileScore(60);

            when(profileMapper.selectById(1L)).thenReturn(profile);
            when(preferenceMapper.selectAllByUserId(1L)).thenReturn(List.of());

            UserProfileVO result = service.getProfile(1L);

            assertThat(result.getUserId()).isEqualTo(1L);
            assertThat(result.getBudgetMax()).isEqualByComparingTo(new BigDecimal("8000"));
            assertThat(result.getPreferredCategories()).containsExactlyInAnyOrder("手机", "电脑");

            // 验证回写缓存
            verify(cacheManager).put(any(UserProfileVO.class));
        }

        @Test
        @DisplayName("画像不存在时抛出BizException")
        void throwsWhenProfileNotFound() {
            when(cacheManager.get(99L)).thenReturn(Optional.empty());
            when(profileMapper.selectById(99L)).thenReturn(null);

            assertThatThrownBy(() -> service.getProfile(99L))
                    .isInstanceOf(BizException.class)
                    .hasMessageContaining("用户画像不存在");
        }

        @Test
        @DisplayName("userId非法时抛出BizException")
        void throwsOnInvalidUserId() {
            assertThatThrownBy(() -> service.getProfile(0L))
                    .isInstanceOf(BizException.class)
                    .hasMessageContaining("userId非法");

            assertThatThrownBy(() -> service.getProfile(null))
                    .isInstanceOf(BizException.class);
        }
    }

    // ==================== 偏好权重更新测试 ====================

    @Nested
    @DisplayName("updatePreferenceWeight - 偏好权重更新")
    class UpdatePreferenceWeightTests {

        @Test
        @DisplayName("新偏好记录 - 插入并设初始权重")
        void insertsNewPreference() {
            when(preferenceMapper.selectOne(any())).thenReturn(null);

            service.updatePreferenceWeight(1L, "brand", "华为", 10);

            verify(preferenceMapper).insert(argThat(pref ->
                    "brand".equals(pref.getDimension()) &&
                    "华为".equals(pref.getDimensionValue()) &&
                    pref.getWeight() == 60 && // 50 + 10
                    "inferred".equals(pref.getSource())
            ));
            verify(cacheManager).evict(1L);
        }

        @Test
        @DisplayName("已有偏好 - 累加权重，上限100")
        void cappedWeightAt100() {
            UserPreference existing = new UserPreference()
                    .setId(10L).setUserId(1L)
                    .setDimension("category").setDimensionValue("手机")
                    .setWeight(98).setTriggerCount(5);

            when(preferenceMapper.selectOne(any())).thenReturn(existing);

            service.updatePreferenceWeight(1L, "category", "手机", 10);

            // 98 + 10 = 108, 限制为100
            verify(preferenceMapper).update(isNull(), argThat(wrapper ->
                    wrapper.toString().contains("weight") ||
                    wrapper.getSqlSet() != null
            ));
            verify(cacheManager).evict(1L);
        }
    }

    // ==================== 初始化测试 ====================

    @Nested
    @DisplayName("initProfile - 初始化用户画像")
    class InitProfileTests {

        @Test
        @DisplayName("新用户正常初始化")
        void initNewProfile() {
            when(profileMapper.selectById(100L)).thenReturn(null);

            service.initProfile(100L, "新用户小明");

            verify(profileMapper).insert(argThat(p ->
                    p.getUserId().equals(100L) &&
                    "新用户小明".equals(p.getNickname())
            ));
        }

        @Test
        @DisplayName("已有画像时跳过初始化（幂等）")
        void skipIfAlreadyExists() {
            when(profileMapper.selectById(100L))
                    .thenReturn(new UserProfile().setUserId(100L));

            service.initProfile(100L, "重复初始化");

            // 不执行insert
            verify(profileMapper, never()).insert(any());
        }
    }

    // ==================== 画像完整度测试 ====================

    @Test
    @DisplayName("refreshProfileScore - 完整信息得100分")
    void fullProfileScores100() {
        UserProfile fullProfile = new UserProfile()
                .setUserId(1L)
                .setGender(1)
                .setAgeGroup("25-35")
                .setCity("广东-深圳")
                .setBudgetMin(new BigDecimal("3000"))
                .setBudgetMax(new BigDecimal("8000"))
                .setPreferredCategories("手机,电脑")
                .setSceneTags("自用,礼物")
                .setPreferredBrands("华为,苹果")
                .setPreferredPlatforms("jd,taobao")
                .setProfileScore(0);

        when(profileMapper.selectById(1L)).thenReturn(fullProfile);

        int score = service.refreshProfileScore(1L);

        // gender(5)+ageGroup(5)+city(5)+budgetMax(20)+budgetMin(10)+categories(20)+scene(10)+brands(15)+platforms(10) = 100
        assertThat(score).isEqualTo(100);
        verify(profileMapper).updateProfileScore(eq(1L), eq(100));
    }
}
