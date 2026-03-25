package com.hd.auth.controller;

import com.hd.auth.dto.LoginDTO;
import com.hd.auth.service.AuthService;
import com.hd.common.result.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    @Autowired
    private AuthService authService;

    @PostMapping("/login")
    public Result<Map<String, Object>> login(@RequestBody LoginDTO dto) {
        Map<String, Object> data = authService.login(dto);
        return Result.success(data);
    }

    @PostMapping("/logout")
    public Result<Void> logout(@RequestHeader(value = "Authorization", required = false) String token) {
        authService.logout(token);
        return Result.success(null);
    }

    @GetMapping("/health")
    public Result<String> health() {
        return Result.success("hd-auth OK");
    }
}
