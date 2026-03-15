package com.ilbuy.l0.profile.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.ilbuy.l0.profile.domain.entity.UserProfile;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

/**
 * 用户画像 Mapper
 *
 * <p>继承 MyBatis-Plus BaseMapper，提供基础CRUD。
 * 复杂查询在 UserProfileMapper.xml 中定义。
 *
 * @author ILbuy Team
 */
@Mapper
public interface UserProfileMapper extends BaseMapper<UserProfile> {

    /**
     * 根据用户ID查询画像（带偏好数据，join查询）
     * 在 UserProfileMapper.xml 中实现
     */
    UserProfile selectWithPreferencesByUserId(@Param("userId") Long userId);

    /**
     * 更新用户画像完整度分
     */
    @Select("UPDATE user_profile SET profile_score = #{score}, updated_at = NOW() " +
            "WHERE user_id = #{userId} AND deleted = 0")
    int updateProfileScore(@Param("userId") Long userId, @Param("score") Integer score);
}
