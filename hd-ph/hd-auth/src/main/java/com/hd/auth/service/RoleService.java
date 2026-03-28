package com.hd.auth.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.hd.auth.entity.SysRole;
import com.hd.auth.entity.SysRolePermission;
import com.hd.auth.mapper.SysRoleMapper;
import com.hd.auth.mapper.SysRolePermissionMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class RoleService {

    @Autowired
    private SysRoleMapper roleMapper;

    @Autowired
    private SysRolePermissionMapper rolePermissionMapper;

    public List<SysRole> listAll() {
        return roleMapper.selectList(new LambdaQueryWrapper<SysRole>().orderByAsc(SysRole::getId));
    }

    public void updateStatus(Long id, Integer status) {
        SysRole role = new SysRole();
        role.setId(id);
        role.setStatus(status);
        roleMapper.updateById(role);
    }

    public List<String> getPermCodesByRoleId(Long roleId) {
        return rolePermissionMapper.selectList(
                new LambdaQueryWrapper<SysRolePermission>().eq(SysRolePermission::getRoleId, roleId)
        ).stream().map(SysRolePermission::getPermCode).collect(java.util.stream.Collectors.toList());
    }

    public SysRole getById(Long id) {
        return roleMapper.selectById(id);
    }

    @Transactional
    public void createRole(SysRole role) {
        roleMapper.insert(role);
    }

    @Transactional
    public void updateRole(SysRole role) {
        roleMapper.updateById(role);
    }

    public void deleteRole(Long id) {
        roleMapper.deleteById(id);
    }

    @Transactional
    public void assignPermissions(Long roleId, List<String> permCodes) {
        rolePermissionMapper.delete(
                new LambdaQueryWrapper<SysRolePermission>().eq(SysRolePermission::getRoleId, roleId)
        );
        if (permCodes != null) {
            for (String permCode : permCodes) {
                SysRolePermission rp = new SysRolePermission();
                rp.setRoleId(roleId);
                rp.setPermCode(permCode);
                rolePermissionMapper.insert(rp);
            }
        }
    }
}
