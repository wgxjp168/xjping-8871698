package com.ilbuy.recommend.model.entity;

import com.ilbuy.recommend.model.enums.RecommendSource;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "recommend_items", indexes = {
    @Index(name = "idx_ri_user_id", columnList = "user_id"),
    @Index(name = "idx_ri_source", columnList = "source"),
    @Index(name = "idx_ri_canonical_id", columnList = "canonical_id"),
    @Index(name = "idx_ri_expires_at", columnList = "expires_at")
})
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RecommendItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id")
    private Long userId;

    @Column(name = "canonical_id")
    private Long canonicalId;

    @Column(name = "platform", length = 50)
    private String platform;

    @Column(name = "product_title", length = 500)
    private String productTitle;

    @Column(name = "image_url", length = 1000)
    private String imageUrl;

    @Column(name = "current_price", precision = 12, scale = 2)
    private BigDecimal currentPrice;

    @Column(name = "score")
    private Double score;

    @Enumerated(EnumType.STRING)
    @Column(name = "source", nullable = false, length = 20)
    private RecommendSource source;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "expires_at")
    private LocalDateTime expiresAt;
}
