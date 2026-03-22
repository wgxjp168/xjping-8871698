-- ============================================================
-- supplier_db 表结构 (04-supplier-db.sql)
-- 包含：供应商信息、供应商评分、店铺信息、店铺评分
-- ============================================================
USE supplier_db;

-- ── 供应商分类 ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `supplier_category` (
  `cate_id`     INT UNSIGNED    NOT NULL AUTO_INCREMENT,
  `cate_name`   VARCHAR(64)     NOT NULL COMMENT '分类名称',
  `parent_id`   INT             NOT NULL DEFAULT 0,
  `sort_order`  INT             NOT NULL DEFAULT 0,
  `status`      TINYINT         NOT NULL DEFAULT 1,
  `create_time` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`cate_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='供应商分类';

-- ── 供应商信息 ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `supplier_info` (
  `supplier_id`      BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '供应商ID',
  `supplier_name`    VARCHAR(128)    NOT NULL COMMENT '供应商名称',
  `cate_id`          INT             NOT NULL DEFAULT 0 COMMENT '分类ID',
  `credit_code`      VARCHAR(64)     DEFAULT '' COMMENT '统一社会信用代码',
  `contact_user`     VARCHAR(64)     DEFAULT '' COMMENT '联系人',
  `contact_phone`    VARCHAR(20)     DEFAULT '' COMMENT '联系电话',
  `address`          VARCHAR(256)    DEFAULT '' COMMENT '地址',
  `qualification`    TEXT            COMMENT '资质证书（JSON数组）',
  `supplier_status`  TINYINT         NOT NULL DEFAULT 0 COMMENT '0=待审 1=正常 2=暂停 3=黑名单',
  `create_time`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`       TINYINT         NOT NULL DEFAULT 0,
  PRIMARY KEY (`supplier_id`),
  KEY `idx_cate_status`  (`cate_id`, `supplier_status`),
  KEY `idx_credit_code`  (`credit_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='供应商信息';

-- ── 供应商评分主表 ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `supplier_score_main` (
  `main_id`        BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '评分主键',
  `supplier_id`    BIGINT UNSIGNED NOT NULL COMMENT '供应商ID',
  `score_period`   VARCHAR(20)     NOT NULL COMMENT '评分周期，如 2024-Q1',
  `total_score`    DECIMAL(5,2)    NOT NULL DEFAULT 0 COMMENT '综合得分',
  `supplier_level` VARCHAR(4)      NOT NULL DEFAULT 'C' COMMENT '等级 S/A/B/C/D',
  `score_user`     VARCHAR(64)     NOT NULL DEFAULT '' COMMENT '评分人',
  `score_time`     DATETIME        NOT NULL COMMENT '评分时间',
  `opinion`        VARCHAR(512)    DEFAULT '' COMMENT '评分意见',
  `create_time`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`main_id`),
  UNIQUE KEY `uk_supplier_period` (`supplier_id`, `score_period`),
  KEY `idx_period`     (`score_period`),
  KEY `idx_level`      (`supplier_level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='供应商评分主表';

-- ── 供应商评分明细 ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `supplier_score_item` (
  `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `main_id`      BIGINT UNSIGNED NOT NULL COMMENT '主表ID',
  `supplier_id`  BIGINT UNSIGNED NOT NULL,
  `score_type`   TINYINT         NOT NULL COMMENT '1=产品质量 2=交付能力 3=成本竞争力 4=合规遵从 5=服务能力 6=稳定性',
  `full_score`   DECIMAL(5,2)    NOT NULL COMMENT '该项满分',
  `actual_score` DECIMAL(5,2)    NOT NULL DEFAULT 0 COMMENT '该项实际得分',
  `remark`       VARCHAR(256)    DEFAULT '',
  `create_time`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_main_id` (`main_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='供应商评分明细';

-- ── 供应商异常记录 ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `supplier_abnormal` (
  `id`             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `supplier_id`    BIGINT UNSIGNED NOT NULL,
  `abnormal_type`  TINYINT         NOT NULL COMMENT '1=交付延误 2=质量问题 3=合规违规 4=价格违约 5=其他',
  `description`    VARCHAR(512)    NOT NULL,
  `handler`        VARCHAR(64)     DEFAULT '',
  `handle_result`  VARCHAR(512)    DEFAULT '',
  `occur_time`     DATETIME        NOT NULL,
  `handle_time`    DATETIME,
  `status`         TINYINT         NOT NULL DEFAULT 0 COMMENT '0=待处理 1=已处理 2=已关闭',
  `create_time`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_supplier_status` (`supplier_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='供应商异常记录';

-- ── 供应商操作日志 ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `supplier_log` (
  `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `supplier_id`  BIGINT UNSIGNED NOT NULL,
  `operate_type` VARCHAR(64)     NOT NULL COMMENT '操作类型',
  `operate_desc` VARCHAR(512)    DEFAULT '',
  `operator`     VARCHAR(64)     NOT NULL DEFAULT '',
  `create_time`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_supplier_time` (`supplier_id`, `create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='供应商操作日志';

-- ── 店铺分类 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `shop_category` (
  `cate_id`    INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `cate_name`  VARCHAR(64)  NOT NULL,
  `parent_id`  INT          NOT NULL DEFAULT 0,
  `sort_order` INT          NOT NULL DEFAULT 0,
  `status`     TINYINT      NOT NULL DEFAULT 1,
  PRIMARY KEY (`cate_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='店铺分类';

-- ── 店铺信息 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `shop_info` (
  `shop_id`       BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `shop_name`     VARCHAR(128)    NOT NULL,
  `cate_id`       INT             NOT NULL DEFAULT 0,
  `contact_user`  VARCHAR(64)     DEFAULT '',
  `contact_phone` VARCHAR(20)     DEFAULT '',
  `shop_status`   TINYINT         NOT NULL DEFAULT 0 COMMENT '0=待审 1=正常 2=暂停',
  `join_time`     DATE,
  `remark`        VARCHAR(256)    DEFAULT '',
  `create_time`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`    TINYINT         NOT NULL DEFAULT 0,
  PRIMARY KEY (`shop_id`),
  KEY `idx_cate_status` (`cate_id`, `shop_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='店铺信息';

-- ── 店铺评分主表 ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `shop_score_main` (
  `main_id`      BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `shop_id`      BIGINT UNSIGNED NOT NULL,
  `score_period` VARCHAR(20)     NOT NULL,
  `total_score`  DECIMAL(5,2)    NOT NULL DEFAULT 0,
  `shop_level`   VARCHAR(4)      NOT NULL DEFAULT 'C',
  `score_user`   VARCHAR(64)     NOT NULL DEFAULT '',
  `score_time`   DATETIME        NOT NULL,
  `opinion`      VARCHAR(512)    DEFAULT '',
  `create_time`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`main_id`),
  UNIQUE KEY `uk_shop_period` (`shop_id`, `score_period`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='店铺评分主表';

-- ── 店铺评分明细 ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `shop_score_item` (
  `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `main_id`      BIGINT UNSIGNED NOT NULL,
  `shop_id`      BIGINT UNSIGNED NOT NULL,
  `score_type`   TINYINT         NOT NULL,
  `full_score`   DECIMAL(5,2)    NOT NULL,
  `actual_score` DECIMAL(5,2)    NOT NULL DEFAULT 0,
  `remark`       VARCHAR(256)    DEFAULT '',
  `create_time`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_main_id` (`main_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='店铺评分明细';

-- ── 店铺违规记录 ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `shop_violation` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `shop_id`         BIGINT UNSIGNED NOT NULL,
  `violation_type`  TINYINT         NOT NULL COMMENT '1=售后违规 2=商品违规 3=履约违规 4=其他',
  `description`     VARCHAR(512)    NOT NULL,
  `penalty_score`   DECIMAL(5,2)    NOT NULL DEFAULT 0 COMMENT '扣分',
  `handler`         VARCHAR(64)     DEFAULT '',
  `handle_result`   VARCHAR(512)    DEFAULT '',
  `occur_time`      DATETIME        NOT NULL,
  `status`          TINYINT         NOT NULL DEFAULT 0,
  `create_time`     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_shop_status` (`shop_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='店铺违规记录';

-- ── 店铺操作日志 ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `shop_operate_log` (
  `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `shop_id`      BIGINT UNSIGNED NOT NULL,
  `operate_type` VARCHAR(64)     NOT NULL,
  `operate_desc` VARCHAR(512)    DEFAULT '',
  `operator`     VARCHAR(64)     NOT NULL DEFAULT '',
  `create_time`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_shop_time` (`shop_id`, `create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='店铺操作日志';

-- ── 初始分类数据 ──────────────────────────────────────────
INSERT IGNORE INTO `supplier_category` (`cate_id`, `cate_name`, `parent_id`) VALUES
  (1, '原材料供应商', 0), (2, '零部件供应商', 0),
  (3, '成品供应商',   0), (4, '服务供应商',   0);

INSERT IGNORE INTO `shop_category` (`cate_id`, `cate_name`, `parent_id`) VALUES
  (1, '电子数码', 0), (2, '服装鞋帽', 0),
  (3, '食品饮料', 0), (4, '工业品',   0);
