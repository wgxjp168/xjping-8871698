package com.ilbuy.gateway.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

import static org.assertj.core.api.Assertions.*;

class JwtUtilTest {

    private static final String SECRET = "ilbuy-user-svc-secret-key-must-be-at-least-32-chars";
    private JwtUtil jwtUtil;

    @BeforeEach
    void setUp() {
        jwtUtil = new JwtUtil(SECRET);
    }

    private String buildToken(long expiresInMs, Long userId, String role, String username) {
        SecretKey key = Keys.hmacShaKeyFor(SECRET.getBytes(StandardCharsets.UTF_8));
        return Jwts.builder()
                .subject(String.valueOf(userId))
                .claim("role", role)
                .claim("username", username)
                .issuedAt(new Date())
                .expiration(new Date(System.currentTimeMillis() + expiresInMs))
                .signWith(key)
                .compact();
    }

    @Test
    void validate_validToken_returnsTrue() {
        String token = buildToken(86_400_000L, 1L, "B2C", "alice");
        assertThat(jwtUtil.validate(token)).isTrue();
    }

    @Test
    void validate_expiredToken_returnsFalse() {
        String token = buildToken(-1000L, 1L, "B2C", "alice");
        assertThat(jwtUtil.validate(token)).isFalse();
    }

    @Test
    void validate_tamperedToken_returnsFalse() {
        String token = buildToken(86_400_000L, 1L, "B2C", "alice") + "tampered";
        assertThat(jwtUtil.validate(token)).isFalse();
    }

    @Test
    void parse_extractsClaims() {
        String token = buildToken(86_400_000L, 42L, "ADMIN", "bob");
        Claims claims = jwtUtil.parse(token);
        assertThat(claims.getSubject()).isEqualTo("42");
        assertThat(claims.get("role", String.class)).isEqualTo("ADMIN");
        assertThat(claims.get("username", String.class)).isEqualTo("bob");
    }

    @Test
    void getUserId_returnsSubject() {
        String token = buildToken(86_400_000L, 99L, "B2B", "corp");
        assertThat(jwtUtil.getUserId(token)).isEqualTo("99");
    }

    @Test
    void getRole_returnsRole() {
        String token = buildToken(86_400_000L, 1L, "B2B", "corp");
        assertThat(jwtUtil.getRole(token)).isEqualTo("B2B");
    }
}
