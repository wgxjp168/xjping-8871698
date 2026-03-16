package com.ilbuy.user.model.dto;

import com.ilbuy.user.model.enums.UserRole;
import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class AuthResponse {
    private String accessToken;
    private String tokenType;
    private long expiresIn;
    private Long userId;
    private String username;
    private UserRole role;
}
