package com.ilbuy.price.repository;

import com.ilbuy.price.model.entity.PriceRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface PriceRecordRepository extends JpaRepository<PriceRecord, Long> {

    /**
     * Get price history for a canonical product on a specific platform within a time window.
     */
    List<PriceRecord> findByCanonicalIdAndPlatformAndRecordedAtAfterOrderByRecordedAtDesc(
        Long canonicalId, String platform, LocalDateTime since);

    /**
     * Get price history for a canonical product across all platforms within a time window.
     */
    List<PriceRecord> findByCanonicalIdAndRecordedAtAfterOrderByRecordedAtDesc(
        Long canonicalId, LocalDateTime since);

    /**
     * Get the latest price record for each platform for a given canonical ID.
     */
    @Query(value = "SELECT pr.* FROM price_records pr " +
        "INNER JOIN (SELECT platform, MAX(recorded_at) AS max_recorded " +
        "            FROM price_records WHERE canonical_id = :canonicalId " +
        "            GROUP BY platform) latest " +
        "ON pr.platform = latest.platform AND pr.recorded_at = latest.max_recorded " +
        "WHERE pr.canonical_id = :canonicalId",
        nativeQuery = true)
    List<PriceRecord> findLatestPricePerPlatform(@Param("canonicalId") Long canonicalId);

    /**
     * Get the latest price record for a specific canonical ID and platform.
     */
    Optional<PriceRecord> findFirstByCanonicalIdAndPlatformOrderByRecordedAtDesc(
        Long canonicalId, String platform);
}
