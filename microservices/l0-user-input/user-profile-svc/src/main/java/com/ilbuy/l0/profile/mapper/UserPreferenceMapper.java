package com.ilbuy.l0.profile.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.ilbuy.l0.profile.domain.entity.UserPreference;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

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
    List<UserPreference> selectByUserIdAndDimension(
            @Param("userId") Long userId,
            @Param("dimension") String dimension
    );

    /**
     * 查询用户所有偏好（按维度+权重排序）
     */
    List<UserPreference> selectAllByUserId(@Param("userId") Long userId);

    /**
     * 增量更新偏好权重（行为触发时调用）
     */
    int incrementWeight(@Param("userId") Long userId,
                        @Param("dimension") String dimension,
                        @Param("dimensionValue") String dimensionValue,
                        @Param("delta") int delta);
}
