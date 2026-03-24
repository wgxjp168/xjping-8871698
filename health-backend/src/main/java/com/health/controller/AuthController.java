package com.health.controller;

import com.health.common.Result;
import com.health.dto.LoginDTO;
import com.health.service.AuthService;
import com.health.vo.LoginVO;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

/**
 * 认证接口
 */
@Api(tags = "认证管理")
@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @ApiOperation("用户登录")
    @PostMapping("/login")
    public Result<LoginVO> login(@Validated @RequestBody LoginDTO dto) {
        return Result.success(authService.login(dto));
    }

    @ApiOperation("退出登录")
    @PostMapping("/logout")
    public Result<Void> logout() {
        // JWT 是无状态的，客户端清除 token 即可
        return Result.success(null, "退出成功");
    }
}
