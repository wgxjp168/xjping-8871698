-- ============================================================
-- ILbuy data-svc — MySQL 8.0 DDL
-- ============================================================

CREATE DATABASE IF NOT EXISTS ilbuy DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ilbuy;

-- ── 商品主表 ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    id               BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
    canonical_id     VARCHAR(128)     NOT NULL COMMENT '全平台唯一标识 {platform}-{productId}',
    platform         VARCHAR(32)      NOT NULL COMMENT '平台标识（TAOBAO/JD/ALI1688/PDD/VIPSHOP/SUNING/DOUYIN）',
    product_id       VARCHAR(128)     NOT NULL COMMENT '平台原始商品ID',
    title_cleaned    VARCHAR(512)              COMMENT '清洗后标题',
    brand_normalised VARCHAR(128)              COMMENT '标准化品牌',
    price            DECIMAL(12,2)             COMMENT '当前售价',
    original_price   DECIMAL(12,2)             COMMENT '原价',
    discount_pct     DOUBLE                    COMMENT '折扣百分比',
    total_score      DOUBLE                    COMMENT '综合评分（0-100）',
    grade            VARCHAR(4)                COMMENT '评级（S/A/B/C）',
    price_score      DOUBLE,
    popularity_score DOUBLE,
    rating_score     DOUBLE,
    availability_score DOUBLE,
    value_for_money_score DOUBLE,
    sales_count      INT                       COMMENT '销量',
    review_count     INT                       COMMENT '评论数',
    average_rating   DOUBLE                    COMMENT '平均评分',
    in_stock         TINYINT(1)   DEFAULT 1    COMMENT '是否有货',
    is_mock          TINYINT(1)   DEFAULT 0    COMMENT '是否测试数据',
    category_path    JSON                      COMMENT '类目路径',
    specs            JSON                      COMMENT '规格属性',
    images           JSON                      COMMENT '图片URL列表',
    crawled_at       DATETIME                  COMMENT '采集时间',
    created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_canonical_id      (canonical_id),
    UNIQUE KEY uk_platform_product  (platform, product_id),
    INDEX idx_brand                 (brand_normalised),
    INDEX idx_total_score           (total_score DESC),
    INDEX idx_crawled_at            (crawled_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='商品主表';

-- ── 历史价格快照 ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS price_history (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    canonical_id  VARCHAR(128)    NOT NULL COMMENT '关联 products.canonical_id',
    price         DECIMAL(12,2)   NOT NULL,
    original_price DECIMAL(12,2),
    discount_pct  DOUBLE,
    recorded_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间',
    PRIMARY KEY (id),
    INDEX idx_canonical_recorded (canonical_id, recorded_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='商品价格历史快照';
