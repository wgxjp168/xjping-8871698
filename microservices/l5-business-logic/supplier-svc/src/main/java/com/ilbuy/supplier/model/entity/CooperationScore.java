package com.ilbuy.supplier.model.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "cooperation_score")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CooperationScore {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "supplier_id", nullable = false)
    private Long supplierId;

    @Column(name = "order_id", nullable = false)
    private Long orderId;

    @Column(name = "score_by", nullable = false)
    private Long scoreBy;

    @Column(name = "quality_score", nullable = false, precision = 4, scale = 2)
    private BigDecimal qualityScore;

    @Column(name = "delivery_score", nullable = false, precision = 4, scale = 2)
    private BigDecimal deliveryScore;

    @Column(name = "service_score", nullable = false, precision = 4, scale = 2)
    private BigDecimal serviceScore;

    @Column(name = "overall_score", nullable = false, precision = 4, scale = 2)
    private BigDecimal overallScore;

    @Column(name = "comment", length = 1000)
    private String comment;

    @CreationTimestamp
    @Column(name = "scored_at", nullable = false, updatable = false)
    private LocalDateTime scoredAt;
}
