package com.ilbuy.supplier.model.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "rfq_quote")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class RfqQuote {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "rfq_id", nullable = false)
    private Long rfqId;

    @Column(name = "supplier_no", nullable = false, length = 30)
    private String supplierNo;

    @Column(name = "unit_price", nullable = false, precision = 19, scale = 2)
    private BigDecimal unitPrice;

    @Column(name = "total_amount", nullable = false, precision = 19, scale = 2)
    private BigDecimal totalAmount;

    @Column(name = "currency", nullable = false, length = 10)
    @Builder.Default
    private String currency = "CNY";

    @Column(name = "delivery_days", nullable = false)
    private Integer deliveryDays;

    @Column(name = "valid_until", nullable = false)
    private LocalDate validUntil;

    @Column(name = "payment_terms", nullable = false, length = 100)
    private String paymentTerms;

    @Column(name = "supplier_remark")
    private String supplierRemark;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;
}
