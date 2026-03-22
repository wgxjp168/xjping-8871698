-- ============================================================
-- ILbuy MySQL 数据库初始化 (00-init-databases.sql)
-- 执行顺序：第一个执行，创建所有数据库
-- ============================================================

-- 用户服务数据库
CREATE DATABASE IF NOT EXISTS user_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 商品服务数据库
CREATE DATABASE IF NOT EXISTS product_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 订单服务数据库
CREATE DATABASE IF NOT EXISTS order_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 供应商服务数据库（含供应商评分 + 店铺评分）
CREATE DATABASE IF NOT EXISTS supplier_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 财务结算数据库
CREATE DATABASE IF NOT EXISTS finance_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 消息通知数据库
CREATE DATABASE IF NOT EXISTS message_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 业务数据服务数据库
CREATE DATABASE IF NOT EXISTS biz_data_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Nacos 配置中心数据库（Nacos 自动建表，此处仅建库）
CREATE DATABASE IF NOT EXISTS nacos_config
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
