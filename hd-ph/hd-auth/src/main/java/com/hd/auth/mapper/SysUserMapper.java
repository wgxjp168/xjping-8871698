package com.hd.auth.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.hd.auth.entity.SysUser;
import com.hd.auth.vo.UserVO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface SysUserMapper extends BaseMapper<SysUser> {

    IPage<UserVO> selectUserPage(Page<UserVO> page,
                                 @Param("username") String username,
                                 @Param("realName") String realName,
                                 @Param("deptId") Long deptId,
                                 @Param("status") Integer status);

    UserVO selectUserVOById(@Param("id") Long id);
}
