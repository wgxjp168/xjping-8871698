package com.ilbuy.datasvc.repository.mysql;

import com.ilbuy.datasvc.model.entity.Product;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Repository
public interface ProductRepository extends JpaRepository<Product, Long> {

    Optional<Product> findByCanonicalId(String canonicalId);

    Optional<Product> findByPlatformAndProductId(String platform, String productId);

    boolean existsByCanonicalId(String canonicalId);

    @Query("SELECT p FROM Product p WHERE p.platform = :platform ORDER BY p.totalScore DESC")
    Page<Product> findByPlatformOrderByScore(@Param("platform") String platform, Pageable pageable);

    @Query("SELECT p FROM Product p WHERE p.grade = :grade AND p.inStock = true ORDER BY p.totalScore DESC")
    List<Product> findTopByGrade(@Param("grade") String grade, Pageable pageable);

    @Query("SELECT p FROM Product p WHERE p.crawledAt >= :since ORDER BY p.crawledAt DESC")
    List<Product> findRecentlyCrawled(@Param("since") Instant since, Pageable pageable);

    @Modifying
    @Query("UPDATE Product p SET p.totalScore = :score, p.grade = :grade WHERE p.canonicalId = :cid")
    int updateScore(@Param("cid") String canonicalId,
                    @Param("score") Double score,
                    @Param("grade") String grade);

    @Query("SELECT COUNT(p) FROM Product p WHERE p.platform = :platform")
    long countByPlatform(@Param("platform") String platform);

    @Query("SELECT p.platform, COUNT(p) FROM Product p GROUP BY p.platform")
    List<Object[]> countGroupByPlatform();
}
