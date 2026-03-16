package com.ilbuy.product.repository;

import com.ilbuy.product.model.entity.PlatformListing;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface PlatformListingRepository extends JpaRepository<PlatformListing, Long> {

    List<PlatformListing> findByCanonicalIdOrderByCurrentPriceAsc(String canonicalId);

    List<PlatformListing> findByCanonicalIdAndPlatformOrderByCurrentPriceAsc(
        String canonicalId, String platform);

    List<PlatformListing> findByCanonicalIdIn(List<String> canonicalIds);
}
