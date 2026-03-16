package com.ilbuy.product.model.entity;

import jakarta.persistence.*;
import lombok.*;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(
    name = "product",
    indexes = {
        @Index(name = "idx_product_canonical_id", columnList = "canonical_id", unique = true),
        @Index(name = "idx_product_category_id",  columnList = "category_id"),
        @Index(name = "idx_product_name",          columnList = "name"),
        @Index(name = "idx_product_enabled",       columnList = "enabled")
    }
)
@EntityListeners(AuditingEntityListener.class)
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Product {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * Canonical / universal product identifier shared across platforms.
     * e.g. "PROD-iphone15pro-256gb-black"
     */
    @Column(name = "canonical_id", nullable = false, unique = true, length = 128)
    private String canonicalId;

    @Column(nullable = false, length = 256)
    private String name;

    @Column(length = 4096)
    private String description;

    @Column(name = "brand", length = 128)
    private String brand;

    @Column(name = "category_id")
    private Long categoryId;

    /** Representative image URL */
    @Column(name = "image_url", length = 512)
    private String imageUrl;

    /** Reference / MSRP price for display */
    @Column(name = "reference_price", precision = 14, scale = 2)
    private BigDecimal referencePrice;

    @Column(nullable = false)
    @Builder.Default
    private Boolean enabled = true;

    /** Comma-separated tags for search */
    @Column(name = "tags", length = 1024)
    private String tags;

    @CreatedDate
    @Column(name = "created_at", updatable = false)
    private Instant createdAt;

    @LastModifiedDate
    @Column(name = "updated_at")
    private Instant updatedAt;
}
