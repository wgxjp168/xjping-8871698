package com.ilbuy.bmonetize.domain;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "api_usage_records", indexes = {
    @Index(name = "idx_api_corp", columnList = "corp_id"),
    @Index(name = "idx_api_period", columnList = "billing_period")
})
@Getter @Setter @Builder @NoArgsConstructor @AllArgsConstructor
public class ApiUsageRecord {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "corp_id", nullable = false)
    private Long corpId;

    @Column(name = "contract_no", length = 64)
    private String contractNo;

    @Column(name = "endpoint", nullable = false, length = 128)
    private String endpoint;

    @Column(name = "call_count", nullable = false) @Builder.Default
    private Long callCount = 1L;

    @Column(name = "billing_period", nullable = false, length = 7)
    private String billingPeriod;   // YYYY-MM

    @Column(name = "unit_price", precision = 10, scale = 4)
    private BigDecimal unitPrice;

    @Column(name = "amount", precision = 12, scale = 2)
    private BigDecimal amount;

    @Column(name = "created_at", nullable = false) @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();
}
