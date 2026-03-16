package com.ilbuy.price.repository;

import com.ilbuy.price.model.entity.BulkPriceTier;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface BulkPriceTierRepository extends JpaRepository<BulkPriceTier, Long> {

    /**
     * Find all bulk price tiers for a product on a specific platform, ordered by minQuantity ASC.
     */
    List<BulkPriceTier> findByCanonicalIdAndPlatformOrderByMinQuantityAsc(String canonicalId, String platform);

    /**
     * Find all bulk price tiers for a product across all platforms, ordered by minQuantity ASC.
     */
    List<BulkPriceTier> findByCanonicalIdOrderByMinQuantityAsc(String canonicalId);
}
