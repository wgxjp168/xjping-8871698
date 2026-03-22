-- ============================================================
-- ILbuy ClickHouse 初始化 DDL (clickhouse-init.sql)
-- 引擎：MergeTree，按日期分区，支持 TTL 自动过期
-- ============================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS ilbuy_analytics;

-- ── 用户行为日志表 ────────────────────────────────────────
-- 每天一个分区，保留 180 天
CREATE TABLE IF NOT EXISTS ilbuy_analytics.user_behavior_log
(
    event_date   Date           COMMENT '事件日期（分区键）',
    event_time   DateTime       COMMENT '事件时间',
    event_id     String         COMMENT '事件唯一ID（UUID）',
    user_id      UInt64         COMMENT '用户ID，0=匿名',
    session_id   String         COMMENT '会话ID',
    event_type   LowCardinality(String) COMMENT '事件类型：page_view/click/search/add_cart/checkout/purchase',
    page         LowCardinality(String) COMMENT '页面标识',
    product_id   UInt64         COMMENT '商品ID，0=非商品页',
    category_id  UInt32         COMMENT '分类ID',
    keyword      String         COMMENT '搜索关键词',
    source       LowCardinality(String) COMMENT '来源渠道：pc/ios/android/mini_program',
    ip           String         COMMENT '客户端IP',
    city         LowCardinality(String) COMMENT '城市',
    device_type  LowCardinality(String) COMMENT '设备类型',
    extra        String         COMMENT '扩展字段 JSON',
    created_at   DateTime       DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(event_date)
ORDER BY (event_date, event_type, user_id)
TTL event_date + INTERVAL 180 DAY
SETTINGS index_granularity = 8192;

-- ── 订单事件日志表 ────────────────────────────────────────
-- 按月分区，保留 3 年
CREATE TABLE IF NOT EXISTS ilbuy_analytics.order_event_log
(
    event_date    Date           COMMENT '事件日期（分区键）',
    event_time    DateTime       COMMENT '事件时间',
    event_id      String         COMMENT '事件唯一ID',
    order_id      UInt64         COMMENT '订单ID',
    order_no      String         COMMENT '订单号',
    user_id       UInt64         COMMENT '用户ID',
    supplier_id   UInt64         COMMENT '供应商ID',
    event_type    LowCardinality(String) COMMENT '事件类型：created/paid/shipped/delivered/completed/cancelled/refunded',
    prev_status   LowCardinality(String) COMMENT '变更前状态',
    curr_status   LowCardinality(String) COMMENT '变更后状态',
    amount        Decimal(12, 4) COMMENT '订单金额',
    pay_method    LowCardinality(String) COMMENT '支付方式',
    source        LowCardinality(String) COMMENT '下单渠道',
    province      LowCardinality(String) COMMENT '收货省份',
    city          LowCardinality(String) COMMENT '收货城市',
    extra         String         COMMENT '扩展字段 JSON',
    created_at    DateTime       DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, event_type, order_id)
TTL event_date + INTERVAL 3 YEAR
SETTINGS index_granularity = 8192;

-- ── 商品搜索日志表 ────────────────────────────────────────
-- 按天分区，保留 90 天（用于热词分析）
CREATE TABLE IF NOT EXISTS ilbuy_analytics.product_search_log
(
    event_date   Date           COMMENT '日期（分区键）',
    event_time   DateTime       COMMENT '搜索时间',
    user_id      UInt64         COMMENT '用户ID',
    keyword      String         COMMENT '搜索关键词',
    result_count UInt32         COMMENT '结果数量',
    clicked_id   UInt64         COMMENT '点击的商品ID，0=未点击',
    source       LowCardinality(String),
    created_at   DateTime       DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(event_date)
ORDER BY (event_date, keyword)
TTL event_date + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

-- ── 物化视图：每日活跃用户统计 ───────────────────────────
CREATE TABLE IF NOT EXISTS ilbuy_analytics.daily_active_users
(
    stat_date    Date,
    source       LowCardinality(String),
    dau          UInt64,
    new_users    UInt64,
    updated_at   DateTime DEFAULT now()
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(stat_date)
ORDER BY (stat_date, source);

-- ── 物化视图：每日订单金额统计 ───────────────────────────
CREATE TABLE IF NOT EXISTS ilbuy_analytics.daily_order_stats
(
    stat_date     Date,
    source        LowCardinality(String),
    order_count   UInt64,
    gmv           Decimal(18, 4),
    cancel_count  UInt64,
    refund_amount Decimal(18, 4),
    updated_at    DateTime DEFAULT now()
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(stat_date)
ORDER BY (stat_date, source);
