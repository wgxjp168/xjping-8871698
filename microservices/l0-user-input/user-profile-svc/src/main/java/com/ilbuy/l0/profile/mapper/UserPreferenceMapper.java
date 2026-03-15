package com.ilbuy.l0.profile.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.ilbuy.l0.profile.domain.entity.UserPreference;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

/**
 * 用户偏好明细 Mapper
 *
 * @author ILbuy Team
 */
@Mapper
public interface UserPreferenceMapper extends BaseMapper<UserPreference> {

    /**
     * 查询用户指定维度的偏好（按权重降序）
     */
    @Select("SELECT * FROM user_preference " +
            "WHERE user_id = #{userId} AND dimension = #{dimension} AND deleted = 0 " +
            "ORDER BY weight DESC")
    List<UserPreference> selectByUserIdAndDimension(
            @Param("userId") Long userId,
            @Param("dimension") String dimension);

    /**
     * 查询用户所有偏好（按维度+权重排序）
     */
    @Select("SELECT * FROM user_preference " +
            "WHERE user_id = #{userId} AND deleted = 0 " +
            "ORDER BY dimension ASC, weight DESC")
    List<UserPreference> selectAllByUserId(@Param("userId") Long userId);

    /**
     * 增量更新偏好权重（限制1-100），同步更新触发计数和时间
     */
    @Update("UPDATE user_preference " +
            "SET weight = LEAST(100, GREATEST(1, weight + #{delta})), " +
            "    trigger_count = trigger_count + 1, " +
            "    last_triggered_at = NOW(), " +
            "    updated_at = NOW() " +
            "WHERE user_id = #{userId} AND dimension = #{dimension} " +
            "  AND dimension_value = #{dimensionValue} AND deleted = 0")
    int incrementWeight(@Param("userId") Long userId,
                        @Param("dimension") String dimension,
                        @Param("dimensionValue") String dimensionValue,
                        @Param("delta") int delta);
}
