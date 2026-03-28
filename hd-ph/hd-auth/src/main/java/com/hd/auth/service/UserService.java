package com.hd.auth.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.hd.auth.dto.UserDTO;
import com.hd.auth.entity.SysUser;
import com.hd.auth.entity.SysUserRole;
import com.hd.auth.mapper.SysUserMapper;
import com.hd.auth.mapper.SysUserRoleMapper;
import com.hd.auth.vo.UserVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class UserService {

    @Autowired
    private SysUserMapper userMapper;

    @Autowired
    private SysUserRoleMapper userRoleMapper;

    @Autowired
    private PasswordEncoder passwordEncoder;

    public List<UserVO> listDoctors(String realName, Long deptId, Integer status) {
        return userMapper.selectDoctors(realName, deptId, status);
    }

    public IPage<UserVO> pageUsers(int current, int size, String username, String realName, Long deptId, Integer status) {
        Page<UserVO> page = new Page<>(current, size);
        return userMapper.selectUserPage(page, username, realName, deptId, status);
    }

    public UserVO getById(Long id) {
        return userMapper.selectUserVOById(id);
    }

    @Transactional
    public void createUser(UserDTO dto) {
        // 检查用户名唯一性
        Long count = userMapper.selectCount(
                new LambdaQueryWrapper<SysUser>().eq(SysUser::getUsername, dto.getUsername()).eq(SysUser::getDeleted, 0)
        );
        if (count > 0) {
            throw new RuntimeException("用户名已存在: " + dto.getUsername());
        }
        SysUser user = new SysUser();
        user.setUsername(dto.getUsername());
        user.setPassword(passwordEncoder.encode(dto.getPassword() != null ? dto.getPassword() : "hd2024"));
        user.setRealName(dto.getRealName());
        user.setPhone(dto.getPhone());
        user.setDeptId(dto.getDeptId());
        user.setUserType(dto.getUserType() != null ? dto.getUserType() : 1);
        user.setStatus(dto.getStatus() != null ? dto.getStatus() : 1);
        userMapper.insert(user);

        if (dto.getRoleIds() != null && !dto.getRoleIds().isEmpty()) {
            for (Long roleId : dto.getRoleIds()) {
                SysUserRole ur = new SysUserRole();
                ur.setUserId(user.getId());
                ur.setRoleId(roleId);
                userRoleMapper.insert(ur);
            }
        }
    }

    @Transactional
    public void updateUser(UserDTO dto) {
        SysUser user = new SysUser();
        user.setId(dto.getId());
        user.setRealName(dto.getRealName());
        user.setPhone(dto.getPhone());
        user.setDeptId(dto.getDeptId());
        user.setUserType(dto.getUserType());
        user.setStatus(dto.getStatus());
        if (dto.getPassword() != null && !dto.getPassword().isEmpty()) {
            user.setPassword(passwordEncoder.encode(dto.getPassword()));
        }
        userMapper.updateById(user);

        if (dto.getRoleIds() != null) {
            userRoleMapper.delete(
                    new LambdaQueryWrapper<SysUserRole>().eq(SysUserRole::getUserId, dto.getId())
            );
            for (Long roleId : dto.getRoleIds()) {
                SysUserRole ur = new SysUserRole();
                ur.setUserId(dto.getId());
                ur.setRoleId(roleId);
                userRoleMapper.insert(ur);
            }
        }
    }

    public void deleteUser(Long id) {
        SysUser user = new SysUser();
        user.setId(id);
        user.setDeleted(1);
        userMapper.updateById(user);
    }

    public void updateStatus(Long id, Integer status) {
        SysUser user = new SysUser();
        user.setId(id);
        user.setStatus(status);
        userMapper.updateById(user);
    }

    public void resetPassword(Long id, String newPassword) {
        SysUser user = new SysUser();
        user.setId(id);
        user.setPassword(passwordEncoder.encode(newPassword));
        userMapper.updateById(user);
    }
}
