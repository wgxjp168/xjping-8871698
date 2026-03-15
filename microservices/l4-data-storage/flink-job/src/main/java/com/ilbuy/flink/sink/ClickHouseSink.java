package com.ilbuy.flink.sink;

import com.ilbuy.flink.model.ProductEvent;
import lombok.extern.slf4j.Slf4j;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.sink.RichSinkFunction;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.List;

/**
 * Flink ClickHouse Sink
 *
 * 批量写入 product_events 分析宽表：
 * - 每 500 条 或 每 5 秒 触发一次批量 INSERT
 * - 写入失败整批重试一次，仍失败则逐条记录日志（保障主流程不中断）
 */
@Slf4j
public class ClickHouseSink extends RichSinkFunction<ProductEvent> {

    private static final long serialVersionUID = 1L;

    private static final int  BATCH_SIZE    = 500;
    private static final long FLUSH_INTERVAL = 5_000L;   // 5s

    private static final String INSERT_SQL =
        "INSERT INTO product_events (" +
        "  canonical_id, platform, product_id, title_cleaned, brand_normalised," +
        "  price, original_price, discount_pct, total_score, grade," +
        "  price_score, popularity_score, rating_score, availability_score, value_for_money_score," +
        "  sales_count, review_count, average_rating, in_stock," +
        "  score_percentile, processed_at, crawled_at" +
        ") VALUES (?,?,?,?,?, ?,?,?,?,?, ?,?,?,?,?, ?,?,?,?, ?,?,?)";

    private final String url;
    private final String user;
    private final String password;

    private transient Connection        connection;
    private transient List<ProductEvent> batch;
    private transient long              lastFlushTime;

    public ClickHouseSink(String url, String user, String password) {
        this.url      = url;
        this.user     = user;
        this.password = password;
    }

    @Override
    public void open(Configuration parameters) throws Exception {
        connection = DriverManager.getConnection(url, user, password);
        connection.setAutoCommit(false);
        batch         = new ArrayList<>(BATCH_SIZE);
        lastFlushTime = System.currentTimeMillis();
        log.info("ClickHouseSink opened: {}", url);
    }

    @Override
    public void invoke(ProductEvent event, Context context) throws Exception {
        if (event == null) {
            return;   // filtered mock records from ProductEnrichTransform
        }
        batch.add(event);

        boolean sizeTrigger = batch.size() >= BATCH_SIZE;
        boolean timeTrigger = (System.currentTimeMillis() - lastFlushTime) >= FLUSH_INTERVAL;

        if (sizeTrigger || timeTrigger) {
            flush();
        }
    }

    private void flush() {
        if (batch.isEmpty()) {
            return;
        }
        List<ProductEvent> toFlush = new ArrayList<>(batch);
        batch.clear();
        lastFlushTime = System.currentTimeMillis();

        try {
            executeBatch(toFlush);
            log.debug("ClickHouseSink flushed {} rows", toFlush.size());
        } catch (Exception e) {
            log.error("Batch flush failed ({}), retrying individually: {}", toFlush.size(), e.getMessage());
            fallbackIndividual(toFlush);
        }
    }

    private void executeBatch(List<ProductEvent> events) throws Exception {
        try (PreparedStatement ps = connection.prepareStatement(INSERT_SQL)) {
            for (ProductEvent ev : events) {
                bindEvent(ps, ev);
                ps.addBatch();
            }
            ps.executeBatch();
            connection.commit();
        } catch (Exception e) {
            try { connection.rollback(); } catch (Exception ignored) {}
            throw e;
        }
    }

    private void fallbackIndividual(List<ProductEvent> events) {
        for (ProductEvent ev : events) {
            try (PreparedStatement ps = connection.prepareStatement(INSERT_SQL)) {
                bindEvent(ps, ev);
                ps.execute();
                connection.commit();
            } catch (Exception e) {
                log.error("Failed to insert event canonicalId={}: {}", ev.getCanonicalId(), e.getMessage());
                try { connection.rollback(); } catch (Exception ignored) {}
            }
        }
    }

    private void bindEvent(PreparedStatement ps, ProductEvent ev) throws Exception {
        ps.setString(1, ev.getCanonicalId());
        ps.setString(2, ev.getPlatform());
        ps.setString(3, ev.getProductId());
        ps.setString(4, ev.getTitleCleaned());
        ps.setString(5, ev.getBrandNormalised());

        ps.setBigDecimal(6,  ev.getPrice());
        ps.setBigDecimal(7,  ev.getOriginalPrice());
        ps.setObject  (8,  ev.getDiscountPct());
        ps.setObject  (9,  ev.getTotalScore());
        ps.setString  (10, ev.getGrade());

        ps.setObject(11, ev.getPriceScore());
        ps.setObject(12, ev.getPopularityScore());
        ps.setObject(13, ev.getRatingScore());
        ps.setObject(14, ev.getAvailabilityScore());
        ps.setObject(15, ev.getValueForMoneyScore());

        ps.setObject(16, ev.getSalesCount());
        ps.setObject(17, ev.getReviewCount());
        ps.setObject(18, ev.getAverageRating());
        ps.setObject(19, ev.getInStock());

        ps.setString   (20, ev.getScorePercentile());
        ps.setTimestamp(21, ev.getProcessedAt() != null
            ? new Timestamp(ev.getProcessedAt()) : null);
        ps.setString   (22, ev.getCrawledAt());
    }

    @Override
    public void close() {
        flush();   // drain remaining buffer
        if (connection != null) {
            try { connection.close(); } catch (Exception e) {
                log.warn("ClickHouseSink close error: {}", e.getMessage());
            }
        }
    }
}
