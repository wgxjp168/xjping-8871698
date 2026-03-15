-- ============================================================
-- ILbuy data-svc — ClickHouse DDL
-- 分析宽表，用于实时流写入与 OLAP 查询
-- ============================================================

CREATE DATABASE IF NOT EXISTS ilbuy_analytics;

-- ── 商品事件流表（主分析表）─────────────────────────────────────
CREATE TABLE IF NOT EXISTS ilbuy_analytics.product_events
(
    -- 标识
    canonical_id          String        COMMENT '全平台唯一标识',
    platform              LowCardinality(String) COMMENT '平台',
    product_id            String        COMMENT '平台原始ID',

    -- 商品基本信息
    title_cleaned         String        COMMENT '清洗标题',
    brand_normalised      LowCardinality(String) COMMENT '品牌',

    -- 价格
    price                 Nullable(Decimal(12,2)) COMMENT '售价',
    original_price        Nullable(Decimal(12,2)) COMMENT '原价',
    discount_pct          Nullable(Float64)       COMMENT '折扣',

    -- 评分体系
    total_score           Nullable(Float64)       COMMENT '综合评分',
    grade                 LowCardinality(String)  COMMENT '评级',
    price_score           Nullable(Float64),
    popularity_score      Nullable(Float64),
    rating_score          Nullable(Float64),
    availability_score    Nullable(Float64),
    value_for_money_score Nullable(Float64),

    -- 销售数据
    sales_count           Nullable(Int32)         COMMENT '销量',
    review_count          Nullable(Int32)         COMMENT '评论数',
    average_rating        Nullable(Float64)       COMMENT '评分均值',
    in_stock              Nullable(UInt8)         COMMENT '库存状态',

    -- Flink 富化字段
    score_percentile      LowCardinality(String)  COMMENT 'TOP10/TOP25/REST',
    processed_at          Nullable(DateTime64(3)) COMMENT 'Flink 处理时间',
    crawled_at            Nullable(String)        COMMENT '采集时间',

    -- ClickHouse 分区字段
    event_date            Date DEFAULT toDate(now()) COMMENT '事件日期（分区键）'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (platform, event_date, canonical_id)
TTL event_date + INTERVAL 2 YEAR
SETTINGS index_granularity = 8192
COMMENT '商品事件实时分析宽表';

-- ── 平台日聚合视图 ──────────────────────────────────────────────
CREATE VIEW IF NOT EXISTS ilbuy_analytics.platform_daily_stats AS
SELECT
    platform,
    event_date,
    count()                             AS total_products,
    avg(total_score)                    AS avg_score,
    countIf(grade = 'S')               AS grade_s_count,
    countIf(grade = 'A')               AS grade_a_count,
    countIf(in_stock = 1)              AS in_stock_count,
    sum(sales_count)                   AS total_sales,
    avg(price)                         AS avg_price
FROM ilbuy_analytics.product_events
GROUP BY platform, event_date;

-- ── 品牌 TOP 视图 ───────────────────────────────────────────────
CREATE VIEW IF NOT EXISTS ilbuy_analytics.brand_top_view AS
SELECT
    brand_normalised,
    platform,
    count()           AS product_count,
    avg(total_score)  AS avg_score,
    sum(sales_count)  AS total_sales
FROM ilbuy_analytics.product_events
WHERE event_date >= today() - 30
GROUP BY brand_normalised, platform
ORDER BY avg_score DESC
LIMIT 100;
