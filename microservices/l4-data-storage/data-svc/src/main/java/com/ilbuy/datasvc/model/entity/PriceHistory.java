package com.ilbuy.datasvc.model.entity;

import jakarta.persistence.*;
import lombok.*;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.math.BigDecimal;
import java.time.Instant;

/**
 * 价格历史表 — 每次 ingest 写入一条价格快照
 * 供 L5 业务层做价格趋势分析
 */
@Entity
@Table(
    name = "price_history",
    indexes = {
        @Index(name = "idx_ph_canonical", columnList = "canonical_id"),
        @Index(name = "idx_ph_recorded",  columnList = "recorded_at"),
    }
)
@EntityListeners(AuditingEntityListener.class)
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class PriceHistory {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "canonical_id", nullable = false, length = 64)
    private String canonicalId;

    @Column(nullable = false, precision = 12, scale = 2)
    private BigDecimal price;

    @Column(name = "original_price", precision = 12, scale = 2)
    private BigDecimal originalPrice;

    @Column(name = "total_score")
    private Double totalScore;

    @CreatedDate
    @Column(name = "recorded_at", updatable = false)
    private Instant recordedAt;
}
