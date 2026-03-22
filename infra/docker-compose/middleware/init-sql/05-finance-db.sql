-- ============================================================
-- finance_db 表结构 (05-finance-db.sql)
-- ============================================================
USE finance_db;

-- ── 发票表 ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_invoice` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `invoice_no`    VARCHAR(64)     NOT NULL COMMENT '发票号码',
  `invoice_type`  VARCHAR(32)     NOT NULL DEFAULT 'special_vat' COMMENT '发票类型',
  `direction`     TINYINT         NOT NULL DEFAULT 1 COMMENT '1=进项 2=销项',
  `supplier_id`   BIGINT UNSIGNED DEFAULT NULL,
  `order_ids`     TEXT            COMMENT '关联订单ID列表 JSON',
  `amount`        DECIMAL(12,4)   NOT NULL COMMENT '不含税金额',
  `tax_rate`      DECIMAL(6,4)    NOT NULL DEFAULT 0.13 COMMENT '税率',
  `tax_amount`    DECIMAL(12,4)   NOT NULL DEFAULT 0 COMMENT '税额',
  `total_amount`  DECIMAL(12,4)   NOT NULL COMMENT '价税合计',
  `issue_date`    DATE            NOT NULL,
  `buyer_name`    VARCHAR(128)    DEFAULT '',
  `buyer_tax_no`  VARCHAR(64)     DEFAULT '',
  `seller_name`   VARCHAR(128)    DEFAULT '',
  `seller_tax_no` VARCHAR(64)     DEFAULT '',
  `status`        TINYINT         NOT NULL DEFAULT 0 COMMENT '0=待验证 1=已验真 2=已拒绝 3=已作废',
  `file_url`      VARCHAR(512)    DEFAULT '' COMMENT '发票文件URL',
  `verified_by`   BIGINT UNSIGNED DEFAULT NULL,
  `verified_at`   DATETIME,
  `reject_reason` VARCHAR(256)    DEFAULT '',
  `create_time`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_invoice_no` (`invoice_no`),
  KEY `idx_supplier`   (`supplier_id`),
  KEY `idx_status`     (`status`),
  KEY `idx_issue_date` (`issue_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='发票表';

-- ── 对账单表 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_reconciliation` (
  `id`                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `recon_no`            VARCHAR(64)     NOT NULL COMMENT '对账单号',
  `supplier_id`         BIGINT UNSIGNED NOT NULL,
  `period_start`        DATE            NOT NULL,
  `period_end`          DATE            NOT NULL,
  `order_amount`        DECIMAL(12,4)   NOT NULL DEFAULT 0 COMMENT '订单金额',
  `invoice_amount`      DECIMAL(12,4)   NOT NULL DEFAULT 0 COMMENT '发票金额',
  `diff_amount`         DECIMAL(12,4)   NOT NULL DEFAULT 0 COMMENT '差异金额',
  `status`              TINYINT         NOT NULL DEFAULT 0 COMMENT '0=草稿 1=已发送 2=有争议 3=已确认 4=已关闭',
  `supplier_confirmed`  TINYINT         NOT NULL DEFAULT 0,
  `confirmed_at`        DATETIME,
  `note`                VARCHAR(512)    DEFAULT '',
  `created_by`          BIGINT UNSIGNED DEFAULT NULL,
  `create_time`         DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time`         DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_recon_no`   (`recon_no`),
  KEY `idx_supplier_period`  (`supplier_id`, `period_start`),
  KEY `idx_status`           (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对账单';

-- ── 结算单表 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `t_settlement` (
  `id`               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `settle_no`        VARCHAR(64)     NOT NULL COMMENT '结算单号',
  `supplier_id`      BIGINT UNSIGNED NOT NULL,
  `reconciliation_id`BIGINT UNSIGNED DEFAULT NULL,
  `invoice_ids`      TEXT            COMMENT '关联发票ID JSON',
  `amount`           DECIMAL(12,4)   NOT NULL,
  `currency`         VARCHAR(8)      DEFAULT 'CNY',
  `payment_method`   VARCHAR(32)     NOT NULL DEFAULT 'bank_transfer',
  `bank_account`     VARCHAR(64)     DEFAULT '',
  `status`           TINYINT         NOT NULL DEFAULT 0 COMMENT '0=待审批 1=已批准 2=已付款 3=已拒绝 4=已取消',
  `apply_at`         DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `approved_at`      DATETIME,
  `paid_at`          DATETIME,
  `approver_id`      BIGINT UNSIGNED DEFAULT NULL,
  `operator_id`      BIGINT UNSIGNED DEFAULT NULL,
  `note`             VARCHAR(512)    DEFAULT '',
  `create_time`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_settle_no`  (`settle_no`),
  KEY `idx_supplier_status`  (`supplier_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='结算单';
