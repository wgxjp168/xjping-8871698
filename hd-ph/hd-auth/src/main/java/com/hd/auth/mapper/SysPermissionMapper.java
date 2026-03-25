package com.hd.auth.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.hd.auth.entity.SysPermission;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface SysPermissionMapper extends BaseMapper<SysPermission> {

    List<String> selectPermCodesByUserId(@Param("userId") Long userId);
}
