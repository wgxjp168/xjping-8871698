package com.ilbuy.datamonetize.domain;

import jakarta.persistence.*;
import lombok.*;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "data_products", indexes = {
    @Index(name = "idx_data_product_code", columnList = "product_code", unique = true)
})
@Getter @Setter @Builder @NoArgsConstructor @AllArgsConstructor
public class DataProduct {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "product_code", nullable = false, unique = true, length = 64)
    private String productCode;

    @Column(name = "name", nullable = false, length = 128)
    private String name;

    @Column(name = "description", columnDefinition = "TEXT")
    private String description;

    @Column(name = "category", nullable = false, length = 32)
    private String category; // MARKET_REPORT, API_DATA, DATA_FEED

    @Column(name = "unit_price", nullable = false, precision = 12, scale = 2)
    private BigDecimal unitPrice;

    @Column(name = "currency", nullable = false, length = 8) @Builder.Default
    private String currency = "CNY";

    @Column(name = "enabled", nullable = false) @Builder.Default
    private Boolean enabled = true;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @PrePersist
    void onCreate() {
        this.createdAt = LocalDateTime.now();
    }
}
