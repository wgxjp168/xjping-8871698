package com.health.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.health.entity.CheckItem;
import org.apache.ibatis.annotations.Mapper;

/**
 * 检查项目 Mapper
 */
@Mapper
public interface CheckItemMapper extends BaseMapper<CheckItem> {
}
