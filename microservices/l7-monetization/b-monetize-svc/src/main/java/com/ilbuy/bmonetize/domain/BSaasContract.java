package com.ilbuy.bmonetize.domain;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "b_saas_contracts", indexes = {
    @Index(name = "idx_contract_no", columnList = "contract_no", unique = true),
    @Index(name = "idx_saas_corp", columnList = "corp_id")
})
@Getter @Setter @Builder @NoArgsConstructor @AllArgsConstructor
public class BSaasContract {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "contract_no", nullable = false, unique = true, length = 64)
    private String contractNo;

    @Column(name = "corp_id", nullable = false)
    private Long corpId;

    @Column(name = "plan_code", nullable = false, length = 32)
    private String planCode;

    @Column(name = "annual_fee", nullable = false, precision = 12, scale = 2)
    private BigDecimal annualFee;

    @Column(name = "api_call_limit")
    private Long apiCallLimit;

    @Column(name = "api_calls_used") @Builder.Default
    private Long apiCallsUsed = 0L;

    /** Maximum team seats (sub-accounts). null = unlimited. */
    @Column(name = "max_seats")
    private Integer maxSeats;

    @Column(name = "start_date", nullable = false)
    private LocalDate startDate;

    @Column(name = "end_date", nullable = false)
    private LocalDate endDate;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 32)
    private ContractStatus status;

    @Column(name = "order_no", length = 64)
    private String orderNo;

    @Column(name = "created_at", nullable = false) @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    public enum ContractStatus { PENDING, ACTIVE, EXPIRED, CANCELLED }

    public boolean isValid() {
        return status == ContractStatus.ACTIVE && !LocalDate.now().isAfter(endDate);
    }

    public boolean hasApiQuota() {
        return isValid() && (apiCallLimit == null || apiCallsUsed < apiCallLimit);
    }
}
