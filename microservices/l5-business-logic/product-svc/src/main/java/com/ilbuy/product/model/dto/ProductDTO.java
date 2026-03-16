package com.ilbuy.product.model.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ProductDTO {

    private Long id;
    private String canonicalId;
    private String name;
    private String description;
    private String brand;
    private Long categoryId;
    private String imageUrl;
    private BigDecimal referencePrice;
    private Boolean enabled;
    private String tags;
    private Instant createdAt;
    private Instant updatedAt;
}
