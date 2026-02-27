package com.ilbuy.business.model;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import java.time.LocalDateTime;

public class User {

    private String id;

    @NotBlank(message = "用户名不能为空")
    private String username;

    @Email(message = "邮箱格式不正确")
    private String email;

    private String phone;
    private String nickname;
    private String avatar;
    private String memberLevel;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public User() {}

    public User(String id, String username, String email, String phone, String nickname) {
        this.id = id;
        this.username = username;
        this.email = email;
        this.phone = phone;
        this.nickname = nickname;
        this.memberLevel = "NORMAL";
        this.createdAt = LocalDateTime.now();
        this.updatedAt = LocalDateTime.now();
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public String getPhone() { return phone; }
    public void setPhone(String phone) { this.phone = phone; }
    public String getNickname() { return nickname; }
    public void setNickname(String nickname) { this.nickname = nickname; }
    public String getAvatar() { return avatar; }
    public void setAvatar(String avatar) { this.avatar = avatar; }
    public String getMemberLevel() { return memberLevel; }
    public void setMemberLevel(String memberLevel) { this.memberLevel = memberLevel; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}
