-- ILbuy测试数据库初始化脚本
USE ilbuy_test;

-- 用户表
CREATE TABLE IF NOT EXISTS `t_user` (
  `id`           BIGINT AUTO_INCREMENT PRIMARY KEY,
  `username`     VARCHAR(64) NOT NULL UNIQUE,
  `password`     VARCHAR(128) NOT NULL,
  `email`        VARCHAR(128),
  `user_type`    ENUM('ENTERPRISE','PERSONAL','SUPPLIER') NOT NULL DEFAULT 'ENTERPRISE',
  `company_name` VARCHAR(128),
  `status`       ENUM('ACTIVE','INACTIVE','PENDING_VERIFY') NOT NULL DEFAULT 'ACTIVE',
  `created_at`   DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_username(`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 采购需求表
CREATE TABLE IF NOT EXISTS `t_procurement_demand` (
  `id`               BIGINT AUTO_INCREMENT PRIMARY KEY,
  `order_no`         VARCHAR(32) NOT NULL UNIQUE,
  `buyer_id`         BIGINT NOT NULL,
  `procurement_type` ENUM('B2B','B2C_DECIDED','B2C_UNDECIDED') NOT NULL,
  `category_id`      INT,
  `product_name`     VARCHAR(256) NOT NULL,
  `product_spec`     VARCHAR(512),
  `quantity`         INT NOT NULL,
  `unit`             VARCHAR(16),
  `budget_amount`    DECIMAL(15,2),
  `currency`         VARCHAR(8) DEFAULT 'CNY',
  `delivery_deadline` DATE,
  `delivery_address` VARCHAR(512),
  `contact_name`     VARCHAR(64),
  `contact_phone`    VARCHAR(20),
  `require_tax`      TINYINT(1) DEFAULT 1,
  `invoice_type`     VARCHAR(32) DEFAULT 'SPECIAL_VAT',
  `remark`           TEXT,
  `status`           ENUM('DRAFT','PENDING_APPROVAL','APPROVED','MATCHING','QUOTED','NEGOTIATING','CONFIRMED','COMPLETED','CANCELLED') NOT NULL DEFAULT 'MATCHING',
  `created_at`       DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at`       DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_buyer(`buyer_id`),
  INDEX idx_status(`status`),
  INDEX idx_created(`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 报价/询价表
CREATE TABLE IF NOT EXISTS `t_inquiry` (
  `id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `demand_id`      BIGINT NOT NULL,
  `buyer_id`       BIGINT NOT NULL,
  `status`         ENUM('SENT','QUOTED','ACCEPTED','EXPIRED','CANCELLED') DEFAULT 'SENT',
  `deadline`       DATETIME,
  `message`        TEXT,
  `created_at`     DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `t_quote` (
  `id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `inquiry_id`     BIGINT NOT NULL,
  `supplier_id`    BIGINT NOT NULL,
  `unit_price`     DECIMAL(15,2),
  `total_amount`   DECIMAL(15,2),
  `tax_rate`       DECIMAL(5,4),
  `delivery_days`  INT,
  `valid_days`     INT,
  `remark`         TEXT,
  `status`         ENUM('SUBMITTED','ACCEPTED','REJECTED','EXPIRED') DEFAULT 'SUBMITTED',
  `created_at`     DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 订单表
CREATE TABLE IF NOT EXISTS `t_order` (
  `id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `order_no`       VARCHAR(32) NOT NULL UNIQUE,
  `demand_id`      BIGINT,
  `buyer_id`       BIGINT NOT NULL,
  `supplier_id`    BIGINT NOT NULL,
  `total_amount`   DECIMAL(15,2),
  `tax_amount`     DECIMAL(15,2),
  `status`         ENUM('PENDING_PAYMENT','PAID','SHIPPING','DELIVERED','COMPLETED','CANCELLED') DEFAULT 'PENDING_PAYMENT',
  `created_at`     DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 供应商表
CREATE TABLE IF NOT EXISTS `t_supplier` (
  `id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `company_name`   VARCHAR(128) NOT NULL,
  `credit_code`    VARCHAR(32),
  `contact_name`   VARCHAR(64),
  `contact_phone`  VARCHAR(20),
  `contact_email`  VARCHAR(128),
  `status`         ENUM('REVIEWING','ACTIVE','SUSPENDED','REJECTED') DEFAULT 'REVIEWING',
  `credit_rating`  VARCHAR(8),
  `avg_score`      DECIMAL(3,2) DEFAULT 5.00,
  `created_at`     DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 市场价格表
CREATE TABLE IF NOT EXISTS `t_market_price` (
  `id`         BIGINT AUTO_INCREMENT PRIMARY KEY,
  `keyword`    VARCHAR(128) NOT NULL,
  `source`     VARCHAR(32) NOT NULL,
  `price`      DECIMAL(15,2),
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_keyword(`keyword`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============ 初始化测试数据 ============
INSERT IGNORE INTO `t_user` (username, password, email, user_type, company_name, status) VALUES
  ('test_buyer_001',    SHA2('Test@123456', 256), 'buyer001@test.com',    'ENTERPRISE', '测试企业采购有限公司', 'ACTIVE'),
  ('test_buyer_002',    SHA2('Test@123456', 256), 'buyer002@test.com',    'ENTERPRISE', '示范科技集团',        'ACTIVE'),
  ('test_supplier_001', SHA2('Test@123456', 256), 'supplier001@test.com', 'SUPPLIER',   NULL,                 'ACTIVE'),
  ('test_supplier_002', SHA2('Test@123456', 256), 'supplier002@test.com', 'SUPPLIER',   NULL,                 'ACTIVE'),
  ('perf_buyer_001',    SHA2('Test@123456', 256), 'perf001@test.com',     'ENTERPRISE', '性能测试企业',        'ACTIVE'),
  ('smoke_test',        SHA2('Test@123456', 256), 'smoke@test.com',       'ENTERPRISE', '冒烟测试账号',        'ACTIVE');

INSERT IGNORE INTO `t_supplier` (id, company_name, credit_code, contact_name, contact_phone, status, credit_rating, avg_score) VALUES
  (5001, '北京文具联盟有限公司', '91110108MA01AB1234', '王销售', '13800001001', 'ACTIVE', 'AAA', 4.80),
  (5002, '上海办公用品总仓',     '91310000MA01CD5678', '李供应', '13800001002', 'ACTIVE', 'AA',  4.60),
  (5003, '深圳数码优选科技',     '91440300MA01EF9012', '张业务', '13800001003', 'ACTIVE', 'AA',  4.50);

INSERT IGNORE INTO `t_market_price` (keyword, source, price) VALUES
  ('A4打印纸', 'JD',     48.00),
  ('A4打印纸', 'TAOBAO', 43.50),
  ('A4打印纸', 'PDD',    38.90),
  ('碳粉盒',   'JD',    280.00),
  ('碳粉盒',   'TAOBAO',260.00),
  ('笔记本电脑','JD',  5999.00),
  ('笔记本电脑','TAOBAO',5699.00);
