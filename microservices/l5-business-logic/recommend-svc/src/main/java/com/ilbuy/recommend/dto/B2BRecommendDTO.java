package com.ilbuy.recommend.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class B2BRecommendDTO {

    /** Based on ORDER history — products the buyer frequently purchases in bulk. */
    private List<RecommendItemDTO> frequentlyPurchased;

    /** Same categories as procurement history — broadens the buyer's sourcing options. */
    private List<RecommendItemDTO> categoryBased;

    /** New items from previously used suppliers — helps buyers discover new stock from trusted sources. */
    private List<RecommendItemDTO> newSupplierProducts;

    /** Recommended supplier numbers based on category match (B2B supplier discovery). */
    private List<String> recommendedSuppliers;
}
