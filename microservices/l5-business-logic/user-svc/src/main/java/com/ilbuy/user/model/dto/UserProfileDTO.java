package com.ilbuy.user.model.dto;

import com.ilbuy.user.model.enums.UserRole;
import lombok.Builder;
import lombok.Data;

import java.time.Instant;

@Data
@Builder
public class UserProfileDTO {
    private Long id;
    private String username;
    private String email;
    private String phone;
    private String nickName;
    private String avatar;
    private UserRole role;
    private String companyName;
    private Instant createdAt;
}
