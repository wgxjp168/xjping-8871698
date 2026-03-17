package com.ilbuy.gateway.domain;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "payment_orders", indexes = {
    @Index(name = "idx_payment_no", columnList = "payment_no", unique = true),
    @Index(name = "idx_biz_order_no", columnList = "biz_order_no"),
    @Index(name = "idx_user_id", columnList = "user_id")
})
@Getter @Setter @Builder @NoArgsConstructor @AllArgsConstructor
public class PaymentOrder {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "payment_no", nullable = false, unique = true, length = 64)
    private String paymentNo;

    @Column(name = "biz_order_no", nullable = false, length = 64)
    private String bizOrderNo;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "amount", nullable = false, precision = 12, scale = 2)
    private BigDecimal amount;

    @Column(name = "currency", length = 8)
    @Builder.Default
    private String currency = "CNY";

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 32)
    private PaymentStatus status;

    @Enumerated(EnumType.STRING)
    @Column(name = "channel", nullable = false, length = 32)
    private PaymentChannel channel;

    @Enumerated(EnumType.STRING)
    @Column(name = "biz_type", nullable = false, length = 32)
    private BizType bizType;

    @Column(name = "subject", length = 256)
    private String subject;

    @Column(name = "channel_order_no", length = 64)
    private String channelOrderNo;

    @Column(name = "channel_resp", columnDefinition = "TEXT")
    private String channelResp;

    @Column(name = "paid_at")
    private LocalDateTime paidAt;

    @Column(name = "expired_at")
    private LocalDateTime expiredAt;

    @Column(name = "created_at", nullable = false)
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PreUpdate
    void onUpdate() { this.updatedAt = LocalDateTime.now(); }

    public enum PaymentStatus { PENDING, PAYING, SUCCESS, FAILED, CANCELLED, REFUNDING, REFUNDED }
    public enum PaymentChannel { WECHAT, ALIPAY, UNIONPAY }
    public enum BizType { C_SINGLE, C_MEMBER, B_SAAS, B_API, B_CUSTOM, DATA_PKG }
}
