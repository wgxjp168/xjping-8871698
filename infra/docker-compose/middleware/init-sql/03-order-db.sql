-- ============================================================
-- order_db 表结构 (03-order-db.sql)
-- ============================================================
USE order_db;

-- ── 订单主表 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_order` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `order_no`        VARCHAR(64)     NOT NULL COMMENT '订单号',
  `user_id`         BIGINT UNSIGNED NOT NULL,
  `receiver_name`   VARCHAR(64)     NOT NULL,
  `receiver_phone`  VARCHAR(20)     NOT NULL,
  `province`        VARCHAR(32)     DEFAULT '',
  `city`            VARCHAR(32)     DEFAULT '',
  `district`        VARCHAR(32)     DEFAULT '',
  `address_detail`  VARCHAR(256)    NOT NULL,
  `status`          TINYINT         NOT NULL DEFAULT 0 COMMENT '0=待付款 1=已付款 2=处理中 3=已发货 4=已签收 5=已完成 6=已取消 7=退款中 8=已退款',
  `total_amount`    DECIMAL(12,4)   NOT NULL DEFAULT 0 COMMENT '商品总额',
  `discount_amount` DECIMAL(12,4)   NOT NULL DEFAULT 0 COMMENT '优惠金额',
  `shipping_fee`    DECIMAL(12,4)   NOT NULL DEFAULT 0 COMMENT '运费',
  `pay_amount`      DECIMAL(12,4)   NOT NULL DEFAULT 0 COMMENT '实付金额',
  `payment_method`  VARCHAR(32)     DEFAULT '' COMMENT 'alipay|wechat|card|balance|cod',
  `paid_at`         DATETIME        COMMENT '支付时间',
  `remark`          VARCHAR(512)    DEFAULT '',
  `cancel_reason`   VARCHAR(256)    DEFAULT '',
  `source`          VARCHAR(32)     DEFAULT 'pc' COMMENT 'pc|ios|android|mini_program|api',
  `create_time`     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time`     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`      TINYINT         NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_user_status`   (`user_id`, `status`),
  KEY `idx_status_time`   (`status`, `create_time`),
  KEY `idx_create_time`   (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单主表';

-- ── 订单明细 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_order_item` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `order_id`      BIGINT UNSIGNED NOT NULL,
  `product_id`    BIGINT UNSIGNED NOT NULL,
  `sku_id`        BIGINT UNSIGNED NOT NULL,
  `product_name`  VARCHAR(256)    NOT NULL COMMENT '下单时商品名快照',
  `sku_attrs`     VARCHAR(512)    DEFAULT '{}' COMMENT 'SKU规格快照',
  `quantity`      INT             NOT NULL,
  `unit_price`    DECIMAL(12,4)   NOT NULL COMMENT '下单时单价',
  `subtotal`      DECIMAL(12,4)   NOT NULL,
  `refund_qty`    INT             NOT NULL DEFAULT 0,
  `refund_amount` DECIMAL(12,4)   NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_order_id`   (`order_id`),
  KEY `idx_product_id` (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单明细';

-- ── 支付记录 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_payment` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `order_id`    BIGINT UNSIGNED NOT NULL,
  `payment_no`  VARCHAR(64)     NOT NULL COMMENT '支付流水号',
  `amount`      DECIMAL(12,4)   NOT NULL,
  `method`      VARCHAR(32)     NOT NULL DEFAULT 'alipay',
  `channel_no`  VARCHAR(128)    DEFAULT '' COMMENT '第三方支付流水号',
  `status`      TINYINT         NOT NULL DEFAULT 0 COMMENT '0=待支付 1=成功 2=失败 3=取消',
  `paid_at`     DATETIME,
  `expired_at`  DATETIME,
  `extra`       TEXT            COMMENT '支付回调原始数据',
  `create_time` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_payment_no` (`payment_no`),
  KEY `idx_order_id` (`order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付记录';

-- ── 退款记录 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_refund` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `order_id`      BIGINT UNSIGNED NOT NULL,
  `payment_id`    BIGINT UNSIGNED DEFAULT NULL,
  `refund_no`     VARCHAR(64)     NOT NULL,
  `amount`        DECIMAL(12,4)   NOT NULL,
  `refund_type`   VARCHAR(32)     DEFAULT 'refund_only' COMMENT 'refund_only|return_refund',
  `reason`        VARCHAR(512)    DEFAULT '',
  `status`        TINYINT         NOT NULL DEFAULT 0 COMMENT '0=待处理 1=已批准 2=已拒绝 3=处理中 4=已完成 5=已取消',
  `reject_reason` VARCHAR(256)    DEFAULT '',
  `apply_at`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `approve_at`    DATETIME,
  `complete_at`   DATETIME,
  `operator_id`   BIGINT UNSIGNED DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_refund_no` (`refund_no`),
  KEY `idx_order_id` (`order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='退款记录';

-- ── 物流信息 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_logistics` (
  `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `order_id`     BIGINT UNSIGNED NOT NULL,
  `company`      VARCHAR(64)     DEFAULT '' COMMENT '快递公司',
  `company_code` VARCHAR(32)     DEFAULT '' COMMENT '快递公司编码',
  `tracking_no`  VARCHAR(64)     DEFAULT '' COMMENT '快递单号',
  `status`       TINYINT         NOT NULL DEFAULT 0 COMMENT '0=待发货 1=运输中 2=派送中 3=已签收 4=异常 5=退件',
  `signed_at`    DATETIME,
  `receiver`     VARCHAR(64)     DEFAULT '',
  `traces`       TEXT            COMMENT '物流轨迹 JSON',
  `create_time`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_order_id`   (`order_id`),
  KEY `idx_tracking_no`(`tracking_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='物流信息';
