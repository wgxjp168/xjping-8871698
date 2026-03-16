package com.ilbuy.user.model.entity;

import com.ilbuy.user.model.enums.UserRole;
import jakarta.persistence.*;
import lombok.*;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.Instant;

@Entity
@Table(
    name = "users",
    indexes = {
        @Index(name = "idx_username", columnList = "username", unique = true),
        @Index(name = "idx_email",    columnList = "email",    unique = true),
        @Index(name = "idx_phone",    columnList = "phone")
    }
)
@EntityListeners(AuditingEntityListener.class)
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 64, unique = true)
    private String username;

    @Column(nullable = false, length = 128, unique = true)
    private String email;

    @Column(nullable = false, length = 256)
    private String password;

    @Column(length = 20)
    private String phone;

    @Column(name = "nick_name", length = 64)
    private String nickName;

    @Column(length = 512)
    private String avatar;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    @Builder.Default
    private UserRole role = UserRole.B2C;

    @Column(nullable = false)
    @Builder.Default
    private Boolean enabled = true;

    @Column(name = "company_name", length = 256)
    private String companyName;

    @Column(name = "credit_limit", precision = 12)
    private java.math.BigDecimal creditLimit;

    @CreatedDate
    @Column(name = "created_at", updatable = false)
    private Instant createdAt;

    @LastModifiedDate
    @Column(name = "updated_at")
    private Instant updatedAt;
}
