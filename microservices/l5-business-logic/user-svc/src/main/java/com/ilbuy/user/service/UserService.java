package com.ilbuy.user.service;

import com.ilbuy.user.model.dto.*;
import com.ilbuy.user.model.entity.User;
import com.ilbuy.user.model.enums.UserRole;
import com.ilbuy.user.repository.UserRepository;
import com.ilbuy.user.security.JwtUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Slf4j
public class UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;

    @Transactional
    public AuthResponse register(RegisterRequest request) {
        if (userRepository.existsByUsername(request.getUsername())) {
            throw new IllegalArgumentException("用户名已存在: " + request.getUsername());
        }
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new IllegalArgumentException("邮箱已注册: " + request.getEmail());
        }

        User user = User.builder()
            .username(request.getUsername())
            .email(request.getEmail())
            .password(passwordEncoder.encode(request.getPassword()))
            .phone(request.getPhone())
            .nickName(request.getNickName())
            .role(request.getRole() != null ? request.getRole() : UserRole.B2C)
            .companyName(request.getCompanyName())
            .enabled(true)
            .build();

        user = userRepository.save(user);
        log.info("New user registered: id={} username={}", user.getId(), user.getUsername());

        String token = jwtUtil.generateToken(user.getId(), user.getUsername(), user.getRole().name());
        return buildAuthResponse(user, token);
    }

    public AuthResponse login(LoginRequest request) {
        User user = userRepository.findByPrincipal(request.getPrincipal())
            .orElseThrow(() -> new IllegalArgumentException("用户不存在"));

        if (!user.getEnabled()) {
            throw new IllegalStateException("账号已被禁用");
        }

        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            throw new IllegalArgumentException("密码错误");
        }

        String token = jwtUtil.generateToken(user.getId(), user.getUsername(), user.getRole().name());
        log.info("User logged in: id={}", user.getId());
        return buildAuthResponse(user, token);
    }

    @Transactional(readOnly = true)
    public UserProfileDTO getProfile(Long userId) {
        User user = userRepository.findById(userId)
            .orElseThrow(() -> new IllegalArgumentException("用户不存在: " + userId));
        return toProfileDTO(user);
    }

    @Transactional
    public UserProfileDTO updateProfile(Long userId, UpdateProfileRequest request) {
        User user = userRepository.findById(userId)
            .orElseThrow(() -> new IllegalArgumentException("用户不存在: " + userId));

        if (request.getNickName()    != null) user.setNickName(request.getNickName());
        if (request.getAvatar()      != null) user.setAvatar(request.getAvatar());
        if (request.getPhone()       != null) user.setPhone(request.getPhone());
        if (request.getCompanyName() != null) user.setCompanyName(request.getCompanyName());

        user = userRepository.save(user);
        return toProfileDTO(user);
    }

    private AuthResponse buildAuthResponse(User user, String token) {
        return AuthResponse.builder()
            .accessToken(token)
            .tokenType("Bearer")
            .expiresIn(jwtUtil.getExpirationMs() / 1000)
            .userId(user.getId())
            .username(user.getUsername())
            .role(user.getRole())
            .build();
    }

    private UserProfileDTO toProfileDTO(User user) {
        return UserProfileDTO.builder()
            .id(user.getId())
            .username(user.getUsername())
            .email(user.getEmail())
            .phone(user.getPhone())
            .nickName(user.getNickName())
            .avatar(user.getAvatar())
            .role(user.getRole())
            .companyName(user.getCompanyName())
            .createdAt(user.getCreatedAt())
            .build();
    }
}
