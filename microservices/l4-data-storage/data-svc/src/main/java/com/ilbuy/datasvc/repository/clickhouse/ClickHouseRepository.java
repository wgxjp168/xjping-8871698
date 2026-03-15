package com.ilbuy.datasvc.repository.clickhouse;

import com.ilbuy.datasvc.model.dto.ProductIngestDTO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * ClickHouse 分析宽表写入
 * 表结构：product_events (MergeTree，按 platform / toYYYYMM(recorded_at) 分区)
 */
@Repository
@RequiredArgsConstructor
@Slf4j
public class ClickHouseRepository {

    private final JdbcTemplate clickhouseJdbcTemplate;

    private static final String INSERT_SQL = """
        INSERT INTO product_events
          (canonical_id, platform, product_id, title_cleaned, brand_normalised,
           price, original_price, discount_pct,
           total_score, grade, price_score, popularity_score, rating_score,
           availability_score, value_for_money_score,
           sales_count, review_count, average_rating, in_stock,
           is_mock, crawled_at, recorded_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """;

    public void insertEvent(ProductIngestDTO dto) {
        try {
            clickhouseJdbcTemplate.update(INSERT_SQL,
                dto.getCanonicalId(),
                dto.getPlatform(),
                dto.getProductId(),
                dto.getTitleCleaned(),
                dto.getBrandNormalised(),
                dto.getPrice(),
                dto.getOriginalPrice(),
                dto.getDiscountPct(),
                dto.getTotalScore(),
                dto.getGrade(),
                dto.getPriceScore(),
                dto.getPopularityScore(),
                dto.getRatingScore(),
                dto.getAvailabilityScore(),
                dto.getValueForMoneyScore(),
                dto.getSalesCount(),
                dto.getReviewCount(),
                dto.getAverageRating(),
                dto.getInStock() != null && dto.getInStock() ? 1 : 0,
                dto.getIsMock() != null && dto.getIsMock() ? 1 : 0,
                Timestamp.from(parseInstant(dto.getCrawledAt())),
                Timestamp.from(Instant.now())
            );
        } catch (Exception e) {
            log.error("ClickHouse insert failed for canonicalId={}: {}", dto.getCanonicalId(), e.getMessage());
        }
    }

    public void batchInsertEvents(List<ProductIngestDTO> dtos) {
        dtos.forEach(this::insertEvent);
    }

    public List<Map<String, Object>> queryPlatformStats() {
        return clickhouseJdbcTemplate.queryForList("""
            SELECT platform,
                   count()                           AS total,
                   avg(total_score)                  AS avg_score,
                   avg(price)                        AS avg_price,
                   countIf(grade = 'A')              AS grade_a_count,
                   max(recorded_at)                  AS last_updated
            FROM product_events
            WHERE recorded_at >= now() - INTERVAL 24 HOUR
            GROUP BY platform
            ORDER BY total DESC
            """);
    }

    public List<Map<String, Object>> queryTopBrands(String platform, int limit) {
        return clickhouseJdbcTemplate.queryForList("""
            SELECT brand_normalised,
                   count()          AS product_count,
                   avg(total_score) AS avg_score,
                   avg(price)       AS avg_price
            FROM product_events
            WHERE platform = ? AND brand_normalised != ''
            GROUP BY brand_normalised
            ORDER BY product_count DESC
            LIMIT ?
            """, platform, limit);
    }

    private Instant parseInstant(String ts) {
        try {
            return ts != null ? Instant.parse(ts) : Instant.now();
        } catch (Exception e) {
            return Instant.now();
        }
    }
}
