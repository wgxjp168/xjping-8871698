package com.ilbuy.billing.domain;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "refund_records")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RefundRecord {

    public enum RefundStatus {
        PENDING, PROCESSING, COMPLETED, FAILED
    }

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false)
    private String refundNo;    // "REF-" + 16 char UUID segment

    @Column(nullable = false)
    private String originalOrderNo;

    @Column(nullable = false)
    private String paymentNo;

    @Column
    private Long userId;

    @Column
    private Long corpId;

    @Column(nullable = false, precision = 19, scale = 4)
    private BigDecimal refundAmount;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String reason;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private RefundStatus status;

    @Column
    private LocalDateTime processedAt;

    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    void prePersist() {
        createdAt = LocalDateTime.now();
    }
}
