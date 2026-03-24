package com.health.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.health.common.PageResult;
import com.health.common.Result;
import com.health.common.exception.BusinessException;
import com.health.entity.SysUser;
import com.health.mapper.SysUserMapper;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.*;

/**
 * 用户管理接口
 */
@Api(tags = "用户管理")
@RestController
@RequestMapping("/user")
@RequiredArgsConstructor
public class UserController {

    private final SysUserMapper userMapper;
    private final PasswordEncoder passwordEncoder;

    @ApiOperation("分页查询用户")
    @GetMapping("/page")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<PageResult<SysUser>> page(
            @RequestParam(defaultValue = "1") int pageNum,
            @RequestParam(defaultValue = "10") int pageSize,
            @RequestParam(required = false) String username,
            @RequestParam(required = false) String role) {
        Page<SysUser> page = new Page<>(pageNum, pageSize);
        LambdaQueryWrapper<SysUser> wrapper = new LambdaQueryWrapper<SysUser>()
                .eq(SysUser::getDeleted, 0)
                .like(StringUtils.hasText(username), SysUser::getUsername, username)
                .eq(StringUtils.hasText(role), SysUser::getRole, role)
                .orderByDesc(SysUser::getCreateTime);
        userMapper.selectPage(page, wrapper);
        return Result.success(PageResult.of(page));
    }

    @ApiOperation("获取用户详情")
    @GetMapping("/{id}")
    public Result<SysUser> getById(@PathVariable Long id) {
        SysUser user = userMapper.selectById(id);
        if (user == null) {
            throw new BusinessException("用户不存在");
        }
        return Result.success(user);
    }

    @ApiOperation("新增用户")
    @PostMapping
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Void> save(@RequestBody SysUser user) {
        user.setPassword(passwordEncoder.encode(user.getPassword()));
        userMapper.insert(user);
        return Result.success();
    }

    @ApiOperation("更新用户")
    @PutMapping
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Void> update(@RequestBody SysUser user) {
        if (StringUtils.hasText(user.getPassword())) {
            user.setPassword(passwordEncoder.encode(user.getPassword()));
        } else {
            user.setPassword(null);
        }
        userMapper.updateById(user);
        return Result.success();
    }

    @ApiOperation("删除用户")
    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Void> delete(@PathVariable Long id) {
        userMapper.deleteById(id);
        return Result.success();
    }

    @ApiOperation("启用/禁用用户")
    @PutMapping("/{id}/status")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Void> toggleStatus(@PathVariable Long id, @RequestParam Integer status) {
        SysUser user = new SysUser();
        user.setId(id);
        user.setStatus(status);
        userMapper.updateById(user);
        return Result.success();
    }
}
