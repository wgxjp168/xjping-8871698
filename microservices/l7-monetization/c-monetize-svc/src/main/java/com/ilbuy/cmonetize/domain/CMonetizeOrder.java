package com.ilbuy.cmonetize.domain;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "c_monetize_orders", indexes = {
    @Index(name = "idx_c_order_no", columnList = "order_no", unique = true),
    @Index(name = "idx_c_user_id", columnList = "user_id"),
    @Index(name = "idx_c_l5_order", columnList = "l5_order_no")
})
@Getter @Setter @Builder @NoArgsConstructor @AllArgsConstructor
public class CMonetizeOrder {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "order_no", nullable = false, unique = true, length = 64)
    private String orderNo;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Enumerated(EnumType.STRING)
    @Column(name = "product_type", nullable = false, length = 32)
    private ProductType productType;

    /** For SINGLE_REPORT: l6ReportNo; for MEMBERSHIP: planCode */
    @Column(name = "product_id", nullable = false, length = 64)
    private String productId;

    @Column(name = "amount", nullable = false, precision = 12, scale = 2)
    private BigDecimal amount;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 32)
    private OrderStatus status;

    @Column(name = "l5_order_no", length = 64)
    private String l5OrderNo;

    @Column(name = "l6_report_no", length = 64)
    private String l6ReportNo;

    @Column(name = "payment_no", length = 64)
    private String paymentNo;

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

    public enum ProductType { SINGLE_REPORT, MEMBERSHIP }
    public enum OrderStatus { PENDING_PAYMENT, PAID, EXPIRED, CANCELLED, REFUNDED }
}
