package com.ilbuy.recommend.model.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "user_profiles")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserProfile {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false, unique = true)
    private Long userId;

    /**
     * JSON array of preferred category names, stored as TEXT.
     * Example: ["electronics","clothing","books"]
     */
    @Column(name = "preferred_categories", columnDefinition = "TEXT")
    private String preferredCategories;

    /**
     * JSON array of preferred platform names, stored as TEXT.
     * Example: ["JD","TAOBAO"]
     */
    @Column(name = "preferred_platforms", columnDefinition = "TEXT")
    private String preferredPlatforms;

    @Column(name = "price_range_min", precision = 12, scale = 2)
    private BigDecimal priceRangeMin;

    @Column(name = "price_range_max", precision = 12, scale = 2)
    private BigDecimal priceRangeMax;

    @Column(name = "total_views")
    @Builder.Default
    private Long totalViews = 0L;

    @Column(name = "total_orders")
    @Builder.Default
    private Long totalOrders = 0L;

    @Column(name = "last_active_at")
    private LocalDateTime lastActiveAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
