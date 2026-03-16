package com.ilbuy.price.model.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "price_records", indexes = {
    @Index(name = "idx_pr_canonical_platform", columnList = "canonical_id, platform"),
    @Index(name = "idx_pr_recorded_at", columnList = "recorded_at")
})
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PriceRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "canonical_id", nullable = false)
    private Long canonicalId;

    @Column(name = "platform", nullable = false, length = 50)
    private String platform;

    @Column(name = "price", nullable = false, precision = 12, scale = 2)
    private BigDecimal price;

    @Column(name = "original_price", precision = 12, scale = 2)
    private BigDecimal originalPrice;

    @Column(name = "currency", length = 10)
    @Builder.Default
    private String currency = "CNY";

    @Column(name = "in_stock")
    @Builder.Default
    private Boolean inStock = true;

    @CreationTimestamp
    @Column(name = "recorded_at", updatable = false)
    private LocalDateTime recordedAt;
}
