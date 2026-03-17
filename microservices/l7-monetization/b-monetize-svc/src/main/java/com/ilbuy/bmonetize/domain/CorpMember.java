package com.ilbuy.bmonetize.domain;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;

/**
 * Team member under a corporate SaaS contract.
 * A corp admin (ADMIN role) manages seats up to the contract's maxSeats limit.
 */
@Entity
@Table(name = "corp_members", indexes = {
    @Index(name = "idx_cm_corp",  columnList = "corp_id"),
    @Index(name = "idx_cm_user",  columnList = "user_id"),
    @Index(name = "idx_cm_corp_user", columnList = "corp_id, user_id", unique = true)
})
@Getter @Setter @Builder @NoArgsConstructor @AllArgsConstructor
public class CorpMember {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "corp_id",  nullable = false)
    private Long corpId;

    @Column(name = "user_id",  nullable = false)
    private Long userId;

    @Column(name = "user_email", length = 128)
    private String userEmail;

    @Column(name = "user_name",  length = 64)
    private String userName;

    @Enumerated(EnumType.STRING)
    @Column(name = "role", nullable = false, length = 16)
    @Builder.Default
    private MemberRole role = MemberRole.MEMBER;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 16)
    @Builder.Default
    private MemberStatus status = MemberStatus.ACTIVE;

    @Column(name = "invited_by")
    private Long invitedBy;

    @Column(name = "created_at", nullable = false) @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "updated_at", nullable = false) @Builder.Default
    private LocalDateTime updatedAt = LocalDateTime.now();

    @PreUpdate
    public void onUpdate() { updatedAt = LocalDateTime.now(); }

    public enum MemberRole   { ADMIN, MEMBER }
    public enum MemberStatus { ACTIVE, DISABLED, INVITED }
}
