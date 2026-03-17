package com.ilbuy.bmonetize.domain;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "b_monetize_orders", indexes = {
    @Index(name = "idx_b_order_no", columnList = "order_no", unique = true),
    @Index(name = "idx_b_corp_id", columnList = "corp_id")
})
@Getter @Setter @Builder @NoArgsConstructor @AllArgsConstructor
public class BMonetizeOrder {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "order_no", nullable = false, unique = true, length = 64)
    private String orderNo;

    @Column(name = "corp_id", nullable = false)
    private Long corpId;

    @Column(name = "contact_user_id", nullable = false)
    private Long contactUserId;

    @Enumerated(EnumType.STRING)
    @Column(name = "product_type", nullable = false, length = 32)
    private ProductType productType;

    @Column(name = "product_id", nullable = false, length = 64)
    private String productId;

    @Column(name = "amount", nullable = false, precision = 12, scale = 2)
    private BigDecimal amount;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 32)
    private OrderStatus status;

    @Column(name = "payment_no", length = 64)
    private String paymentNo;

    @Column(name = "contract_no", length = 64)
    private String contractNo;

    @Column(name = "paid_at")
    private LocalDateTime paidAt;

    @Column(name = "created_at", nullable = false) @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PreUpdate void onUpdate() { this.updatedAt = LocalDateTime.now(); }

    public enum ProductType { SAAS_ANNUAL, API_CALL, B_CUSTOM }
    public enum OrderStatus { PENDING_PAYMENT, PAID, EXPIRED, CANCELLED, REFUNDED }
}
