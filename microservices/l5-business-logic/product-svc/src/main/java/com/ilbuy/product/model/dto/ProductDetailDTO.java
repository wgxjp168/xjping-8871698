package com.ilbuy.product.model.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * Full product detail: product metadata + all platform listings.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ProductDetailDTO {

    private ProductDTO product;

    /** All platform listings for this canonical product, sorted by currentPrice ascending. */
    private List<PlatformListingDTO> listings;
}
