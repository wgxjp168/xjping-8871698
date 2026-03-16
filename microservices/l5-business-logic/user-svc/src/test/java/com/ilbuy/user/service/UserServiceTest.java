package com.ilbuy.user.service;

import com.ilbuy.user.model.dto.LoginRequest;
import com.ilbuy.user.model.dto.RegisterRequest;
import com.ilbuy.user.model.dto.AuthResponse;
import com.ilbuy.user.model.entity.User;
import com.ilbuy.user.model.enums.UserRole;
import com.ilbuy.user.repository.UserRepository;
import com.ilbuy.user.security.JwtUtil;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @Mock UserRepository userRepository;
    @Mock JwtUtil jwtUtil;

    PasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    UserService userService;

    @BeforeEach
    void setUp() {
        userService = new UserService(userRepository, passwordEncoder, jwtUtil);
    }

    @Test
    void register_success() {
        RegisterRequest req = new RegisterRequest();
        req.setUsername("alice");
        req.setEmail("alice@example.com");
        req.setPassword("pass1234");
        req.setRole(UserRole.B2C);

        when(userRepository.existsByUsername("alice")).thenReturn(false);
        when(userRepository.existsByEmail("alice@example.com")).thenReturn(false);

        User savedUser = User.builder()
            .id(1L).username("alice").email("alice@example.com")
            .password("encoded").role(UserRole.B2C).enabled(true)
            .build();
        when(userRepository.save(any(User.class))).thenReturn(savedUser);
        when(jwtUtil.generateToken(1L, "alice", "B2C")).thenReturn("jwt-token");
        when(jwtUtil.getExpirationMs()).thenReturn(86400000L);

        AuthResponse resp = userService.register(req);

        assertThat(resp.getAccessToken()).isEqualTo("jwt-token");
        assertThat(resp.getUserId()).isEqualTo(1L);
        assertThat(resp.getRole()).isEqualTo(UserRole.B2C);
    }

    @Test
    void register_duplicateUsername_throws() {
        RegisterRequest req = new RegisterRequest();
        req.setUsername("alice");
        req.setEmail("alice@example.com");
        req.setPassword("pass1234");
        req.setRole(UserRole.B2C);

        when(userRepository.existsByUsername("alice")).thenReturn(true);

        assertThatThrownBy(() -> userService.register(req))
            .isInstanceOf(IllegalArgumentException.class)
            .hasMessageContaining("用户名已存在");
    }

    @Test
    void login_success() {
        String rawPass = "pass1234";
        String encoded = passwordEncoder.encode(rawPass);

        User user = User.builder()
            .id(2L).username("bob").email("bob@example.com")
            .password(encoded).role(UserRole.B2B).enabled(true)
            .build();

        when(userRepository.findByPrincipal("bob")).thenReturn(Optional.of(user));
        when(jwtUtil.generateToken(2L, "bob", "B2B")).thenReturn("jwt-bob");
        when(jwtUtil.getExpirationMs()).thenReturn(86400000L);

        LoginRequest req = new LoginRequest();
        req.setPrincipal("bob");
        req.setPassword(rawPass);

        AuthResponse resp = userService.login(req);
        assertThat(resp.getAccessToken()).isEqualTo("jwt-bob");
    }

    @Test
    void login_wrongPassword_throws() {
        String encoded = passwordEncoder.encode("correctPass");
        User user = User.builder()
            .id(3L).username("carol").password(encoded).enabled(true).role(UserRole.B2C)
            .build();

        when(userRepository.findByPrincipal("carol")).thenReturn(Optional.of(user));

        LoginRequest req = new LoginRequest();
        req.setPrincipal("carol");
        req.setPassword("wrongPass");

        assertThatThrownBy(() -> userService.login(req))
            .isInstanceOf(IllegalArgumentException.class)
            .hasMessageContaining("密码错误");
    }
}
