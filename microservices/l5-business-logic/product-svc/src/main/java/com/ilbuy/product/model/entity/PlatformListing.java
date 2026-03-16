package com.ilbuy.product.model.entity;

import jakarta.persistence.*;
import lombok.*;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.math.BigDecimal;
import java.time.Instant;

/**
 * Represents one product listing on a specific e-commerce platform
 * (JD / Taobao / PDD / etc.).  Multiple listings can share the same
 * canonicalId — they are all offerings of the same canonical product.
 */
@Entity
@Table(
    name = "platform_listing",
    indexes = {
        @Index(name = "idx_listing_canonical_id", columnList = "canonical_id"),
        @Index(name = "idx_listing_platform",     columnList = "platform"),
        @Index(name = "idx_listing_in_stock",     columnList = "in_stock")
    }
)
@EntityListeners(AuditingEntityListener.class)
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class PlatformListing {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** Links back to Product.canonicalId */
    @Column(name = "canonical_id", nullable = false, length = 128)
    private String canonicalId;

    /** Platform code: jd / taobao / pdd / tmall … */
    @Column(nullable = false, length = 32)
    private String platform;

    /** Deep link to the product page on the external platform */
    @Column(name = "external_url", length = 1024)
    private String externalUrl;

    @Column(name = "current_price", nullable = false, precision = 14, scale = 2)
    private BigDecimal currentPrice;

    @Column(name = "original_price", precision = 14, scale = 2)
    private BigDecimal originalPrice;

    /** ISO-4217 currency code, default CNY */
    @Column(length = 8)
    @Builder.Default
    private String currency = "CNY";

    @Column(name = "in_stock", nullable = false)
    @Builder.Default
    private Boolean inStock = true;

    /** Timestamp of last price/stock sync from the external platform */
    @Column(name = "last_sync_at")
    private Instant lastSyncAt;

    @CreatedDate
    @Column(name = "created_at", updatable = false)
    private Instant createdAt;

    @LastModifiedDate
    @Column(name = "updated_at")
    private Instant updatedAt;
}
