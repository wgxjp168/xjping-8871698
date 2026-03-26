package com.hd.auth.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.hd.auth.dto.LoginDTO;
import com.hd.auth.entity.SysUser;
import com.hd.auth.mapper.SysPermissionMapper;
import com.hd.auth.mapper.SysUserMapper;
import com.hd.common.util.JwtUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Service
public class AuthService {

    @Autowired
    private AuthenticationManager authenticationManager;

    @Autowired
    private SysUserMapper sysUserMapper;

    @Autowired
    private SysPermissionMapper sysPermissionMapper;

    @Autowired
    private StringRedisTemplate redisTemplate;

    @Autowired
    private JwtUtils jwtUtils;

    public Map<String, Object> login(LoginDTO dto) {
        try {
            Authentication authentication = authenticationManager.authenticate(
                    new UsernamePasswordAuthenticationToken(dto.getUsername(), dto.getPassword())
            );
        } catch (AuthenticationException e) {
            throw new RuntimeException("用户名或密码错误");
        }

        SysUser user = sysUserMapper.selectOne(
                new LambdaQueryWrapper<SysUser>()
                        .eq(SysUser::getUsername, dto.getUsername())
                        .eq(SysUser::getDeleted, 0)
        );
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }

        List<String> permissions = sysPermissionMapper.selectPermCodesByUserId(user.getId());

        String token = jwtUtils.generateToken(user.getId(), user.getUsername(), permissions);

        // 更新最后登录时间
        SysUser update = new SysUser();
        update.setId(user.getId());
        update.setLastLoginTime(LocalDateTime.now());
        sysUserMapper.updateById(update);

        Map<String, Object> result = new HashMap<>();
        result.put("token", token);
        result.put("userId", user.getId());
        result.put("username", user.getUsername());
        result.put("realName", user.getRealName());
        result.put("userType", user.getUserType());
        result.put("permissions", permissions);
        return result;
    }

    public void logout(String token) {
        if (token != null && token.startsWith("Bearer ")) {
            token = token.substring(7);
        }
        if (token != null && !token.isEmpty()) {
            // 加入黑名单，保留24小时（key需与Gateway的JwtAuthFilter一致）
            redisTemplate.opsForValue().set(
                    "token:logout:" + token, "1", 24, TimeUnit.HOURS
            );
        }
    }
}
