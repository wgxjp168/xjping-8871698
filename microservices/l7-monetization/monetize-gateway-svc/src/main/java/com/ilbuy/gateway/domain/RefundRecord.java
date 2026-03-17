package com.ilbuy.gateway.domain;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "refund_records", indexes = {
    @Index(name = "idx_refund_no", columnList = "refund_no", unique = true),
    @Index(name = "idx_payment_no_refund", columnList = "payment_no")
})
@Getter @Setter @Builder @NoArgsConstructor @AllArgsConstructor
public class RefundRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "refund_no", nullable = false, unique = true, length = 64)
    private String refundNo;

    @Column(name = "payment_no", nullable = false, length = 64)
    private String paymentNo;

    @Column(name = "biz_order_no", nullable = false, length = 64)
    private String bizOrderNo;

    @Column(name = "refund_amount", nullable = false, precision = 12, scale = 2)
    private BigDecimal refundAmount;

    @Column(name = "reason", length = 256)
    private String reason;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 32)
    private RefundStatus status;

    @Column(name = "channel_refund_no", length = 64)
    private String channelRefundNo;

    @Column(name = "channel_resp", columnDefinition = "TEXT")
    private String channelResp;

    @Column(name = "refunded_at")
    private LocalDateTime refundedAt;

    @Column(name = "created_at", nullable = false)
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    public enum RefundStatus { PENDING, PROCESSING, SUCCESS, FAILED }
}
