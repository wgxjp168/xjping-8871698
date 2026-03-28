package com.hd.auth.controller;

import com.hd.auth.entity.SysPermission;
import com.hd.auth.mapper.SysPermissionMapper;
import com.hd.common.result.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/permissions")
public class PermissionController {

    @Autowired
    private SysPermissionMapper permissionMapper;

    @GetMapping
    public Result<List<SysPermission>> list() {
        return Result.success(permissionMapper.selectList(null));
    }
}
