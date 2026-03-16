package com.ilbuy.product.repository;

import com.ilbuy.product.model.entity.Product;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

public interface ProductRepository extends JpaRepository<Product, Long> {

    Optional<Product> findByCanonicalId(String canonicalId);

    Page<Product> findByEnabledTrue(Pageable pageable);

    Page<Product> findByCategoryIdAndEnabledTrue(Long categoryId, Pageable pageable);

    /**
     * Basic keyword + category + price range search using LIKE (ES fallback).
     * At least one of name / description / brand / tags must contain the keyword.
     */
    @Query("""
        SELECT p FROM Product p
        WHERE p.enabled = true
          AND (:keyword IS NULL OR :keyword = ''
               OR LOWER(p.name) LIKE LOWER(CONCAT('%', :keyword, '%'))
               OR LOWER(p.description) LIKE LOWER(CONCAT('%', :keyword, '%'))
               OR LOWER(p.brand) LIKE LOWER(CONCAT('%', :keyword, '%'))
               OR LOWER(p.tags) LIKE LOWER(CONCAT('%', :keyword, '%')))
          AND (:categoryId IS NULL OR p.categoryId = :categoryId)
          AND (:minPrice IS NULL OR p.referencePrice >= :minPrice)
          AND (:maxPrice IS NULL OR p.referencePrice <= :maxPrice)
        """)
    Page<Product> searchProducts(
        @Param("keyword")    String keyword,
        @Param("categoryId") Long categoryId,
        @Param("minPrice")   BigDecimal minPrice,
        @Param("maxPrice")   BigDecimal maxPrice,
        Pageable pageable
    );

    List<Product> findAllByIdIn(List<Long> ids);
}
