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
@Table(name = "price_alerts", indexes = {
    @Index(name = "idx_pa_user_id", columnList = "user_id"),
    @Index(name = "idx_pa_triggered", columnList = "triggered"),
    @Index(name = "idx_pa_canonical_platform", columnList = "canonical_id, platform")
})
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PriceAlert {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "canonical_id", nullable = false)
    private Long canonicalId;

    @Column(name = "platform", length = 50)
    private String platform;

    @Column(name = "target_price", nullable = false, precision = 12, scale = 2)
    private BigDecimal targetPrice;

    @Column(name = "triggered")
    @Builder.Default
    private Boolean triggered = false;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "triggered_at")
    private LocalDateTime triggeredAt;
}
