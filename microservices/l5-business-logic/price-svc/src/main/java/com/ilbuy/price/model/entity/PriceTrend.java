package com.ilbuy.price.model.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.Date;

@Entity
@Table(name = "price_trends", indexes = {
    @Index(name = "idx_pt_canonical_platform_date", columnList = "canonical_id, platform, date")
})
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PriceTrend {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "canonical_id", nullable = false)
    private Long canonicalId;

    @Column(name = "platform", nullable = false, length = 50)
    private String platform;

    @Temporal(TemporalType.DATE)
    @Column(name = "date", nullable = false)
    private Date date;

    @Column(name = "min_price", precision = 12, scale = 2)
    private BigDecimal minPrice;

    @Column(name = "max_price", precision = 12, scale = 2)
    private BigDecimal maxPrice;

    @Column(name = "avg_price", precision = 12, scale = 2)
    private BigDecimal avgPrice;
}
