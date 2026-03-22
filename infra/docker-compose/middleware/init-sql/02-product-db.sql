-- ============================================================
-- product_db 表结构 (02-product-db.sql)
-- ============================================================
USE product_db;

-- ── 商品分类 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_category` (
  `id`          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
  `name`        VARCHAR(64)     NOT NULL COMMENT '分类名称',
  `parent_id`   INT UNSIGNED    DEFAULT 0 COMMENT '父分类ID，0=顶级',
  `level`       TINYINT         NOT NULL DEFAULT 1 COMMENT '层级 1-3',
  `path`        VARCHAR(256)    DEFAULT '' COMMENT '层级路径，如 1/2/3',
  `icon_url`    VARCHAR(512)    DEFAULT '',
  `sort_order`  INT             NOT NULL DEFAULT 0,
  `status`      TINYINT         NOT NULL DEFAULT 1 COMMENT '1=启用 0=禁用',
  `create_time` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_parent_id` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商品分类';

-- ── 商品主表 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_product` (
  `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `category_id`  INT UNSIGNED    NOT NULL COMMENT '分类ID',
  `supplier_id`  BIGINT UNSIGNED DEFAULT NULL COMMENT '供应商ID',
  `name`         VARCHAR(256)    NOT NULL COMMENT '商品名称',
  `subtitle`     VARCHAR(512)    DEFAULT '' COMMENT '副标题',
  `description`  TEXT            COMMENT '详情描述',
  `cover_image`  VARCHAR(512)    DEFAULT '' COMMENT '主图URL',
  `unit`         VARCHAR(32)     DEFAULT '件' COMMENT '单位',
  `weight`       DECIMAL(10,3)   DEFAULT 0 COMMENT '重量(kg)',
  `status`       TINYINT         NOT NULL DEFAULT 1 COMMENT '0=草稿 1=上架 2=下架 3=停产',
  `is_featured`  TINYINT         NOT NULL DEFAULT 0 COMMENT '是否推荐',
  `tags`         VARCHAR(512)    DEFAULT '' COMMENT '标签，逗号分隔',
  `sales_count`  INT             NOT NULL DEFAULT 0 COMMENT '销量',
  `view_count`   INT             NOT NULL DEFAULT 0 COMMENT '浏览量',
  `create_time`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`   TINYINT         NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_category_status` (`category_id`, `status`),
  KEY `idx_supplier`        (`supplier_id`),
  KEY `idx_status`          (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商品主表';

-- ── 商品 SKU ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_product_sku` (
  `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `product_id`   BIGINT UNSIGNED NOT NULL,
  `sku_code`     VARCHAR(64)     NOT NULL COMMENT 'SKU编码',
  `barcode`      VARCHAR(64)     DEFAULT '' COMMENT '条码',
  `attributes`   VARCHAR(1024)   DEFAULT '{}' COMMENT '规格属性 JSON',
  `cost_price`   DECIMAL(12,4)   NOT NULL DEFAULT 0 COMMENT '成本价',
  `market_price` DECIMAL(12,4)   NOT NULL DEFAULT 0 COMMENT '市场价',
  `sale_price`   DECIMAL(12,4)   NOT NULL DEFAULT 0 COMMENT '销售价',
  `status`       TINYINT         NOT NULL DEFAULT 1,
  `create_time`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sku_code` (`sku_code`),
  KEY `idx_product_id` (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商品SKU';

-- ── 库存表 ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_product_inventory` (
  `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `sku_id`       BIGINT UNSIGNED NOT NULL,
  `warehouse_id` INT             NOT NULL DEFAULT 1 COMMENT '仓库ID',
  `quantity`     INT             NOT NULL DEFAULT 0 COMMENT '可用库存',
  `reserved`     INT             NOT NULL DEFAULT 0 COMMENT '预占库存',
  `safety_stock` INT             NOT NULL DEFAULT 0 COMMENT '安全库存',
  `update_time`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sku_warehouse` (`sku_id`, `warehouse_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='库存表';

-- ── 商品图片 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_product_image` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `product_id`  BIGINT UNSIGNED NOT NULL,
  `sku_id`      BIGINT UNSIGNED DEFAULT NULL,
  `url`         VARCHAR(512)    NOT NULL,
  `sort_order`  INT             NOT NULL DEFAULT 0,
  `is_cover`    TINYINT         NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_product_id` (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商品图片';

-- ── 分类初始数据 ──────────────────────────────────────────
INSERT IGNORE INTO `t_category` (`id`, `name`, `parent_id`, `level`, `path`) VALUES
  (1,  '电子设备',   0, 1, '1'),
  (2,  '办公用品',   0, 1, '2'),
  (3,  '工业原材料', 0, 1, '3'),
  (4,  '服装配饰',   0, 1, '4'),
  (11, '电脑整机',   1, 2, '1/11'),
  (12, '手机通讯',   1, 2, '1/12'),
  (21, '打印耗材',   2, 2, '2/21'),
  (22, '文具',       2, 2, '2/22');
