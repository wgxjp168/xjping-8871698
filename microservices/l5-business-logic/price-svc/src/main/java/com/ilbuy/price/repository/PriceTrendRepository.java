package com.ilbuy.price.repository;

import com.ilbuy.price.model.entity.PriceTrend;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Date;
import java.util.List;

@Repository
public interface PriceTrendRepository extends JpaRepository<PriceTrend, Long> {

    /**
     * Find trend data for a canonical product on a specific platform within a date range.
     */
    List<PriceTrend> findByCanonicalIdAndPlatformAndDateAfterOrderByDateAsc(
        Long canonicalId, String platform, Date since);

    /**
     * Find trend data for a canonical product across all platforms within a date range.
     */
    List<PriceTrend> findByCanonicalIdAndDateAfterOrderByDateAsc(
        Long canonicalId, Date since);

    /**
     * Aggregate weekly trends from daily trend data.
     */
    @Query(value = "SELECT MIN(id) AS id, canonical_id, platform, " +
        "MIN(date) AS date, MIN(min_price) AS min_price, MAX(max_price) AS max_price, " +
        "AVG(avg_price) AS avg_price " +
        "FROM price_trends " +
        "WHERE canonical_id = :canonicalId AND platform = :platform AND date >= :since " +
        "GROUP BY canonical_id, platform, YEARWEEK(date, 1) " +
        "ORDER BY date ASC",
        nativeQuery = true)
    List<PriceTrend> findWeeklyTrend(@Param("canonicalId") Long canonicalId,
                                     @Param("platform") String platform,
                                     @Param("since") Date since);

    /**
     * Aggregate monthly trends from daily trend data.
     */
    @Query(value = "SELECT MIN(id) AS id, canonical_id, platform, " +
        "MIN(date) AS date, MIN(min_price) AS min_price, MAX(max_price) AS max_price, " +
        "AVG(avg_price) AS avg_price " +
        "FROM price_trends " +
        "WHERE canonical_id = :canonicalId AND platform = :platform AND date >= :since " +
        "GROUP BY canonical_id, platform, YEAR(date), MONTH(date) " +
        "ORDER BY date ASC",
        nativeQuery = true)
    List<PriceTrend> findMonthlyTrend(@Param("canonicalId") Long canonicalId,
                                      @Param("platform") String platform,
                                      @Param("since") Date since);
}
