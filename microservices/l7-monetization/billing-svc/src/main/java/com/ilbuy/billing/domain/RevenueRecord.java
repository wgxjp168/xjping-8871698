package com.ilbuy.billing.domain;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "revenue_records")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RevenueRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 7)
    private String period;      // "YYYY-MM"

    @Column(nullable = false)
    private String orderType;

    @Column(nullable = false)
    private Integer orderCount;

    @Column(nullable = false, precision = 19, scale = 4)
    private BigDecimal totalRevenue;

    @Column(nullable = false, precision = 19, scale = 4)
    private BigDecimal refundAmount;

    @Column(nullable = false, precision = 19, scale = 4)
    private BigDecimal netRevenue;

    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    void prePersist() {
        createdAt = LocalDateTime.now();
    }
}
