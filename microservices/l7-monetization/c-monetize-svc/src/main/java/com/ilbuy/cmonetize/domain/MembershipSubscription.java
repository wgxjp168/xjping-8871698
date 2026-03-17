package com.ilbuy.cmonetize.domain;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "membership_subscriptions", indexes = {
    @Index(name = "idx_sub_no", columnList = "subscription_no", unique = true),
    @Index(name = "idx_sub_user", columnList = "user_id")
})
@Getter @Setter @Builder @NoArgsConstructor @AllArgsConstructor
public class MembershipSubscription {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "subscription_no", nullable = false, unique = true, length = 64)
    private String subscriptionNo;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "plan_code", nullable = false, length = 32)
    private String planCode;

    @Column(name = "start_date", nullable = false)
    private LocalDate startDate;

    @Column(name = "end_date", nullable = false)
    private LocalDate endDate;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 32)
    private SubscriptionStatus status;

    @Column(name = "auto_renew", nullable = false)
    @Builder.Default
    private Boolean autoRenew = false;

    @Column(name = "reports_used")
    @Builder.Default
    private Integer reportsUsed = 0;

    @Column(name = "order_no", length = 64)
    private String orderNo;

    @Column(name = "created_at", nullable = false)
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    public enum SubscriptionStatus { ACTIVE, EXPIRED, CANCELLED }

    public boolean isValid() {
        return status == SubscriptionStatus.ACTIVE && !LocalDate.now().isAfter(endDate);
    }
}
