package com.ilbuy.datamonetize.domain;

import jakarta.persistence.*;
import lombok.*;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "data_orders", indexes = {
    @Index(name = "idx_data_order_no", columnList = "order_no", unique = true),
    @Index(name = "idx_data_order_user_id", columnList = "user_id"),
    @Index(name = "idx_data_order_corp_id", columnList = "corp_id")
})
@Getter @Setter @Builder @NoArgsConstructor @AllArgsConstructor
public class DataOrder {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "order_no", nullable = false, unique = true, length = 64)
    private String orderNo;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "corp_id")
    private Long corpId;

    @Column(name = "product_code", nullable = false, length = 64)
    private String productCode;

    @Column(name = "product_name", nullable = false, length = 128)
    private String productName;

    @Column(name = "unit_price", nullable = false, precision = 12, scale = 2)
    private BigDecimal unitPrice;

    @Column(name = "quantity", nullable = false) @Builder.Default
    private Integer quantity = 1;

    @Column(name = "total_amount", nullable = false, precision = 12, scale = 2)
    private BigDecimal totalAmount;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 32)
    private OrderStatus status;

    @Column(name = "payment_no", length = 64)
    private String paymentNo;

    @Column(name = "report_job_no", length = 64)
    private String reportJobNo; // links to L6 report

    @Column(name = "paid_at")
    private LocalDateTime paidAt;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @PrePersist
    void onCreate() {
        this.createdAt = LocalDateTime.now();
    }

    public enum OrderStatus {
        PENDING_PAYMENT, PAID, FULFILLED, CANCELLED, REFUNDED
    }
}
